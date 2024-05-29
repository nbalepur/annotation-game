import asyncio
from typing import Dict
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async as to_async
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.core.serializers import serialize

from .models import *
from .utils import clean_content, generate_name, generate_id
from .judge import judge_answer_annotation_game

import json
import datetime
import random
import logging
import threading

logger = logging.getLogger('django')

GRACE_TIME = 3

class QuizbowlConsumer(AsyncJsonWebsocketConsumer):
    """Websocket consumer for quizbowl game
    """

    async def connect(self):
        """Websocket connect"""
        self.room_name = self.scope['url_route']['kwargs']['label']
        self.room_group_name = f"game-{self.room_name}"
        
        # Join room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """Websocket disconnect"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Websocket receive"""
        data = json.loads(text_data)
        if 'content' not in data or data['content'] is None:
            data['content'] = ''

        room: Room = await to_async(Room.objects.get)(label=self.room_name)

        # Handle new user and join room
        if data['request_type'] == 'new_user':
            user = await self.new_user(room)
            data['user_id'] = user.user_id
            await self.join(room, data)

        # Abort if no user id or request type supplied
        if 'user_id' not in data or 'request_type' not in data:
            return

        # Validate user
        users_with_same_id = await to_async(User.objects.filter)(user_id=data['user_id'])
        if await to_async(users_with_same_id.count)() <= 0:
            user = await self.new_user(room)
            data['user_id'] = user.user_id

        # Handle join
        if data['request_type'] == 'join':
            await self.join(room, data)
            return

        # Get player
        p: Player = await room.aget_player_by_id(data['user_id'])
        if p is not None:

            # Kick if banned user
            if p.banned:
                await self.kick()
                return

            # Handle requests for joined players
            if data['request_type'] == 'ping':
                await self.ping(room, p)
            elif data['request_type'] == 'leave':
                await self.leave(room, p)
            # elif data['request_type'] == 'get_shown_question':
            #     await self.get_shown_question(room)
            elif data['request_type'] == 'get_answer':
                await self.get_answer(room)
            elif data['request_type'] == 'get_current_question_feedback':
                await self.get_init_question_feedback(room, p)
            elif data['request_type'] == 'set_user_data':
                await self.set_user_data(room, p, data['content'])
            elif data['request_type'] == 'next':
                await self.next(room, p)
                # await self.send_question(room, 60 / room.speed)
            elif data['request_type'] == 'buzz_init':
                await self.buzz_init(room, p)
            elif data['request_type'] == 'buzz_answer':
                await self.buzz_answer(room, p, data['content'])
            elif data['request_type'] == 'submit_initial_feedback':
                await self.submit_initial_feedback(room, p, data['content'])
            elif data['request_type'] == 'submit_additional_feedback':
                await self.submit_additional_feedback(room, p, data['content'])
            elif data['request_type'] == 'set_category':
                await self.set_category(room, p, data['content'])
            elif data['request_type'] == 'set_difficulty':
                await self.set_difficulty(room, p, data['content'])
            elif data['request_type'] == 'set_speed':
                await self.set_speed(room, p, data['content'])
            elif data['request_type'] == 'reset_score':
                await self.reset_score(room, p)
            elif data['request_type'] == 'chat':
                await self.chat(room, p, data['content'])
            elif data['request_type'] == 'report_message':
                await self.report_message(room, p, data['content'])
            else:
                pass

    async def update_room(self, event):
        """Room update handler"""
        await self.send_json(event['data'])

    async def ping(self, room, p):
        """Receive ping"""
        p.last_seen = timezone.now().timestamp()
        await to_async(p.save)()

        await update_time_state(room)

        await self.send_json(await to_async(get_room_response_json)(room))
        await self.send_json({
            'response_type': 'lock_out',
            'locked_out': p.locked_out,
        })

    async def join(self, room: Room, data):
        """Join room"""
        def get_user(user_id):
            return User.objects.filter(user_id=user_id).first()

        user: User = await to_async(get_user)(data['user_id'])
        if user is None:
            return

        # Create player if doesn't exist
        p = await to_async(user.players.filter(room=room).first)()

        # Get the players in the room that have last been seen within 10 seconds ago, excluding the user trying to join
        num_current_players = await to_async(room.players.filter(
            Q(last_seen__gte=timezone.now().timestamp() - 10) &
            ~Q(user__user_id=data['user_id'])
        ).count)()

        if p is None and num_current_players < room.max_players:
            p = await to_async(Player.objects.create)(room=room, user=user)
        
        if num_current_players >= room.max_players:
            await self.too_many_players()
        else:
            # await create_message("join", p, None, room)

            await self.send_json(await to_async(get_room_response_json)(room))

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': await to_async(get_room_response_json)(room),
                }
            )

            if await room.aget_current_question():
                await self.get_shown_question(room=room)
                await self.get_answer(room=room)

    async def leave(self, room, p):
        """Leave room"""
        # await create_message("leave", p, None, room)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': await to_async(get_room_response_json)(room),
            }
        )

    async def new_user(self, room):
        """Create new user and player in room"""
        user = await to_async(User.objects.create)(
            user_id=generate_id(), name=generate_name()
        )

        await self.send_json({
            "response_type": "new_user",
            "user_id": user.user_id,
            "user_name": user.name,
        })

        return user

    async def set_user_data(self, room, p: Player, content):
        """Update player name"""
        user = await p.aget_user()
        user.name = clean_content(content["user_name"])
        user.email = clean_content(content["user_email"])
        try:
            await to_async(p.user.full_clean)()
            await to_async(p.user.save)()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': await to_async(get_room_response_json)(room),
                }
            )

        except ValidationError:
            return

    async def next(self, room: Room, player: Player):
        """Next question"""
        update_time_state(room)

        if room.state == 'idle':
            questions = (
                await to_async(list)(Question.objects.filter(difficulty=room.difficulty).all())
                    if room.category == 'Everything' else 
                await to_async(list)(Question.objects.filter(Q(category=room.category) & Q(difficulty=room.difficulty)).all())
            )

            if room.collects_feedback:
                current_question = await room.aget_current_question()
                if current_question:
                    current_feedback = await to_async(QuestionFeedback.objects.get)(player=player, question=current_question)
                    
                    # Do not execute next if not finished with feedback
                    if not await to_async(current_feedback.is_completed)():
                        return

                # Get the IDs of questions with feedback from the player
                questions_ids_with_feedback = [
                    (await feedback.aget_question()).question_id async for feedback in 
                    await to_async(player.feedback.all)()
                ]

                # Exclude questions with feedback from the player
                questions_without_feedback = (
                    await to_async(list)(
                        Question.objects.exclude(question_id__in=questions_ids_with_feedback).filter(
                            Q(category=room.category) & Q(difficulty=room.difficulty)
                        )
                        .all()
                    )
                )

                questions = questions_without_feedback if len(questions_without_feedback) > 0 else questions

            # Abort if no questions
            if len(questions) <= 0:
                return

            q = random.choice(questions)

            room.state = 'playing'
            room.start_time = timezone.now().timestamp()
            room.end_time = room.start_time + (len(q.content.split()) - 1) / (room.speed / 60)  # start_time (sec since epoch) + words in question / (words/sec)
            room.current_question = q

            await to_async(room.save)()

            # Unlock all players
            for p in await to_async(list)(room.players.all()):
                p.locked_out = False
                await to_async(p.save)()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': await to_async(get_room_response_json)(room),
                }
            )

            await self.send_next_question(room=room, interval=60 / room.speed)
    
    async def send_next_question(self, room: Room, interval: float):
        while room.state == Room.GameState.PLAYING:
            await self.get_shown_question(room=room)
            await asyncio.sleep(interval)

    async def buzz_init(self, room, p):
        """Initialize buzz"""
        # Reject when not in contest
        if room.state != Room.GameState.PLAYING:
            return

        # Abort if no current question
        if await room.aget_current_question() is None:
            return

        if not p.locked_out and room.state == Room.GameState.PLAYING:
            room.state = Room.GameState.CONTEST
            room.buzz_player = p
            room.buzz_start_time = timezone.now().timestamp()
            await to_async(room.save)()

            p.locked_out = True
            await to_async(p.save)()

            # await create_message("buzz_init", p, None, room)

            await self.send_json({
                'response_type': 'buzz_grant',
            })
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': await to_async(get_room_response_json)(room),
                }
            )

    async def buzz_answer(self, room: Room, player: Player, content):
        """Handle buzz answer"""
        # Reject when not in contest
        if room.state != Room.GameState.CONTEST:
            return

        # Abort if no buzz player or current question
        buzz_player: Player = await room.aget_buzz_player()
        current_question: Question = await room.aget_current_question()
        if buzz_player is None or current_question is None:
            return

        if player.player_id == buzz_player.player_id:
            cleaned_content = clean_content(content)
            answered_correctly = judge_answer_annotation_game(cleaned_content, current_question)
            # answered_correctly: bool = judge_answer_kuiperbowl(cleaned_content, await room.aget_current_question().answer)
            words_to_show = room.compute_words_to_show()

            if answered_correctly:
                player.score += 10  # TODO: do not hardcode points
                player.correct += 1
                await to_async(player.save)()

                # Quick end question
                room.end_time = room.start_time
                room.buzz_player = None
                room.state = Room.GameState.IDLE
                await to_async(room.save)()

                await create_message(
                    "buzz_correct",
                    player,
                    cleaned_content,
                    room,
                )
            else:
                if room.max_players == 1:
                    # Quick end question
                    room.end_time = room.start_time
                    room.state = Room.GameState.IDLE
                else:
                    room.state = Room.GameState.PLAYING

                room.buzz_player = None
                await to_async(room.save)()

                # Question reading ended, do penalty
                if room.end_time - room.buzz_start_time >= GRACE_TIME:
                    player.score -= 10
                    player.negs += 1
                    await to_async(player.save)()

                await create_message(
                    "buzz_wrong",
                    player,
                    cleaned_content,
                    room,
                )

                await self.send_json({
                    "response_type": "lock_out",
                    "locked_out": True,
                })

                buzz_duration = timezone.now().timestamp() - room.buzz_start_time
                room.start_time += buzz_duration
                room.end_time += buzz_duration
                await to_async(room.save)()

            current_question = await room.aget_current_question()
            try:
                feedback = await to_async(QuestionFeedback.objects.get)(
                    question=current_question, player=player
                )
            except QuestionFeedback.DoesNotExist:
                feedback = await to_async(QuestionFeedback.objects.create)(
                    question=current_question,
                    player=player,
                    guessed_answer=cleaned_content,
                    submitted_clue_list=current_question.clue_list,
                    submitted_clue_order=list(range(current_question.length)),
                    submitted_factual_mask_list=[True] * current_question.length,
                    answered_correctly=answered_correctly,
                    buzzed=True,
                    buzz_position_word=words_to_show,
                    buzz_position_norm=words_to_show / len(current_question.content.split()),
                    buzz_datetime=timezone.now()
                )
                await to_async(feedback.save)()
            except ValidationError:
                pass

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': await to_async(get_room_response_json)(room),
                }
            )

        # Forfeit question if buzz time up
        elif timezone.now().timestamp() >= room.buzz_start_time + GRACE_TIME:
            buzz_duration = timezone.now().timestamp() - room.buzz_start_time
            room.state = Room.GameState.PLAYING
            room.start_time += buzz_duration
            room.end_time += buzz_duration
            await to_async(room.save)()

            await create_message(
                "buzz_forfeit",
                room.buzz_player,
                None,
                room,
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': await to_async(get_room_response_json)(room),
                }
            )

    async def submit_initial_feedback(self, room: Room, player: Player, content):
        """Submit initial feedback"""
        if room.state == 'idle':
            try:
                current_question = await room.aget_current_question()
                feedback = await to_async(QuestionFeedback.objects.get)(
                    question=current_question, player=player
                )
                if feedback.initial_submission_datetime is None:
                    feedback.guessed_generation_method = content['guessed_generatation_method']
                    feedback.interestingness_rating = content['interestingness_rating']
                    feedback.initial_submission_datetime = timezone.now()
                    feedback.is_submitted = True

                    feedback.solicit_additional_feedback = (
                        feedback.guessed_generation_method == Question.GenerationMethod.AI or
                        not current_question.is_human_written
                    )

                    feedback.guessed_gen_method_correctly = (
                        (current_question.is_human_written and feedback.guessed_generation_method == Question.GenerationMethod.HUMAN)
                        or
                        (not current_question.is_human_written and feedback.guessed_generation_method == Question.GenerationMethod.AI)
                    )

                    await to_async(feedback.save)()
            except ValidationError:
                print(f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}")
            except KeyError as e:
                print(f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}")
                print(f"KeyError: {e}")

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': {
                        "response_type": "get_question_feedback",
                        "question_feedback": get_question_feedback_response_json(feedback),
                    },
                }
            )

    async def submit_additional_feedback(self, room: Room, player: Player, content):
        """Submit additional feedback"""
        if room.state == 'idle':
            try:
                current_question = await room.aget_current_question()
                feedback = await to_async(QuestionFeedback.objects.get)(
                    question=current_question, player=player
                )
                if feedback.additional_submission_datetime is None:
                    feedback.submitted_clue_order = content['submitted_clue_order']
                    feedback.submitted_factual_mask_list = content['submitted_factual_mask_list']

                    # When counting inversions, we should ignore clues marked non-factual, since untrue things probably
                    # shouldn't have a "difficulty"
                    clue_order_for_factual_clues = list(
                        filter(lambda i: feedback.submitted_factual_mask_list[i], feedback.submitted_clue_order)
                    )
                    feedback.inversions = count_inversions(clue_order_for_factual_clues)
                    feedback.submitted_clue_list = [current_question.clue_list[i] for i in feedback.submitted_clue_order]

                    feedback.improved_question = content['improved_question']
                    feedback.feedback_text = content['feedback_text']
                    feedback.additional_submission_datetime = timezone.now()
                    feedback.is_submitted = True

                    await to_async(feedback.save)()
            except ValidationError:
                print(f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}")
            except KeyError as e:
                print(f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}")
                print(f"KeyError: {e}")

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': {
                        "response_type": "get_question_feedback",
                        "question_feedback": get_question_feedback_response_json(feedback),
                    },
                }
            )

    async def get_answer(self, room):
        """Get answer for room question"""
        update_time_state(room)

        if room.state == 'idle':
            current_question: Question = await room.aget_current_question()

            # Generate random question for now if empty
            if current_question is None:
                questions = await to_async(Question.objects.all)()

                # Abort if no questions
                if await to_async(questions.count)() <= 0:
                    return

                q = random.choice(questions)
                room.current_question = q
                await to_async(room.save)()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': {
                        "response_type": "send_answer",
                        "answer": current_question.answer,
                    },
                }
            )

    async def get_shown_question(self, room: Room):
        """Computes the correct amount of the question to show, depending on the state of the game."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': {
                    "response_type": "get_shown_question",
                    "shown_question": await to_async(room.get_shown_question)(),
                },
            }
        )

    async def get_init_question_feedback(self, room: Room, player: Player):
        """After a question is completed (i.e. the room becomes idle),
        send a message containing the feedback regarding the question"""
        if room.state is Room.GameState.IDLE:
            return

        current_question = await room.aget_current_question()

        try:
            feedback = await to_async(QuestionFeedback.objects.get)(
                question=current_question, player=player
            )
        except QuestionFeedback.DoesNotExist:
            feedback = await to_async(QuestionFeedback.objects.create)(
                question=current_question,
                player=player,
                submitted_clue_list=current_question.clue_list,
                submitted_clue_order=list(range(current_question.length)),
                submitted_factual_mask_list=[True] * current_question.length,
                answered_correctly=False,
                buzz_position_word=len(current_question.content.split()),
                buzz_position_norm=1
            )
            await to_async(feedback.save)()
        except ValidationError:
            pass

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': {
                    "response_type": "get_question_feedback",
                    "question_feedback": get_question_feedback_response_json(feedback),
                },
            }
        )

    async def set_category(self, room, p, content):
        """Set room category"""
        # Abort if change locked
        if room.change_locked:
            return

        try:
            room.category = clean_content(content)
            await to_async(room.full_clean)()
            await to_async(room.save)()

            await create_message(
                "set_category",
                p,
                room.category,
                room,
            )
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': await to_async(get_room_response_json)(room),
                }
            )
        except ValidationError:
            pass

    async def set_difficulty(self, room, p, content):
        """Set room difficulty"""
        # Abort if change locked
        if room.change_locked:
            return

        try:
            room.difficulty = clean_content(content)
            await to_async(room.full_clean)()
            await to_async(room.save)()

            await create_message(
                "set_difficulty",
                p,
                room.difficulty,
                room,
            )
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': await to_async(get_room_response_json)(room),
                }
            )
        except ValidationError:
            pass

    async def set_speed(self, room, p, content):
        """Set room speed"""
        # Abort if change locked

        try:
            room.speed = int(clean_content(content))
            await to_async(room.full_clean)()
            await to_async(room.save)()

            await create_message(
                "set_speed",
                p,
                room.speed,
                room,
            )
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': await to_async(get_room_response_json)(room),
                }
            )
        except ValidationError as e:
            print(e)
            pass

    async def reset_score(self, room, p):
        """Reset player score"""
        p.score = 0
        await to_async(p.save)()

        await create_message("reset_score", p, None, room)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': await to_async(get_room_response_json)(room),
            }
        )

    async def chat(self, room, p, content):
        """Send chat message"""
        m = clean_content(content)

        await create_message("chat", p, m, room)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': await to_async(get_room_response_json)(room),
            }
        )

    async def kick(self):
        """Kick banned player"""
        await self.send_json({
            "response_type": "kick",
        })
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )

    async def too_many_players(self):
        """Too many players in a room. Cannot join room."""
        await self.send_json({
            "response_type": "too_many_players",
        })
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )

    async def report_message(self, room, p, message_id):
        """Handle reporting messages"""
        m = await to_async(room.messages.filter)(message_id=message_id).first()
        if m is None:
            return

        # Only report chat or buzz messages
        if m.tag == 'chat' or m.tag == 'buzz_correct' or m.tag == 'buzz_wrong':
            m.player.reported_by.add(p)
            await to_async(m.save)()

            # Ban if reported by 60% of players
            ratio = len(m.player.reported_by.all()) / len(room.players.all())
            if ratio > 0.6:
                m.player.banned = True
                await to_async(m.player.save)()

# === Helper methods ===

async def update_time_state(room):
    """Checks time and updates state"""
    if not room.state == 'contest':
        if timezone.now().timestamp() >= room.end_time + GRACE_TIME:
            room.state = 'idle'
            await to_async(room.save)()

def get_room_response_json(room: Room):
    """Generates JSON for update response"""
    return {
        "response_type": "update",
        "game_state": room.state,
        "current_time": timezone.now().timestamp(),
        "start_time": room.start_time,
        "end_time": room.end_time,
        "buzz_start_time": room.buzz_start_time,
        "category": room.current_question.category if room.current_question is not None else "",
        "room_category": room.category,
        "messages": room.get_messages(),
        "difficulty": room.difficulty,
        "speed": room.speed,
        "players": room.get_players_by_score(),
        "change_locked": room.change_locked,
    }

def get_question_feedback_response_json(feedback: QuestionFeedback) -> Dict:
    # Serialize the feedback object to JSON
    feedback_json = serialize('json', [feedback])
    
    # Convert serialized data to dictionary
    feedback_dict = json.loads(feedback_json)[0]['fields']
    
    return feedback_dict

async def create_message(tag, p, content, room):
    """Adds a message to db"""
    try:
        m = Message(tag=tag, player=p, content=content, room=room)
        await to_async(m.full_clean)()
        await to_async(m.save)()
    except ValidationError:
        return

def count_inversions(arr):
    def merge(arr, left, mid, right):
        temp = []
        i = left
        j = mid + 1
        inv_count = 0
        
        while i <= mid and j <= right:
            if arr[i] <= arr[j]:
                temp.append(arr[i])
                i += 1
            else:
                temp.append(arr[j])
                j += 1
                inv_count += mid - i + 1
        
        temp.extend(arr[i:mid + 1])
        temp.extend(arr[j:right + 1])
        arr[left:right + 1] = temp
        
        return inv_count

    def merge_sort(arr, left, right):
        inv_count = 0
        if left < right:
            mid = (left + right) // 2
            inv_count += merge_sort(arr, left, mid)
            inv_count += merge_sort(arr, mid + 1, right)
            inv_count += merge(arr, left, mid, right)
        return inv_count

    return merge_sort(arr, 0, len(arr) - 1)