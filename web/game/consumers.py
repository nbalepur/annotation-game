import math
from copy import deepcopy
from typing import Dict
from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError
from django.db.models import Q
from channels.generic.websocket import JsonWebsocketConsumer

from django.core.serializers import serialize
from django.http import JsonResponse

from .models import *
from .utils import clean_content, generate_name, generate_id
from .judge import judge_answer_kuiperbowl, judge_answer_annotation_game

import json
import datetime
import random
import logging

logger = logging.getLogger('django')

GRACE_TIME = 3

# TODO: Use channels authentication?


class QuizbowlConsumer(JsonWebsocketConsumer):
    """Websocket consumer for quizbowl game
    """

    def connect(self):
        """Websocket connect
        """
        self.room_name = self.scope['url_route']['kwargs']['label']
        self.room_group_name = f"game-{self.room_name}"
    
        # Join room
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        """Websocket disconnect
        """
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        """Websocket receive
        """
        data = json.loads(text_data)
        if 'content' not in data or data['content'] == None:
            data['content'] = ''

        room = Room.objects.get(label=self.room_name)

        # Handle new user and join room
        if data['request_type'] == 'new_user':
            user = self.new_user(room)
            data['user_id'] = user.user_id
            self.join(room, data)

        # Abort if no user id or request type supplied
        if 'user_id' not in data or 'request_type' not in data:
            return

        # Validate user
        if len(User.objects.filter(user_id=data['user_id'])) <= 0:
            user = self.new_user(room)
            data['user_id'] = user.user_id

        # Handle join
        if data['request_type'] == 'join':
            self.join(room, data)
            return

        # Get player
        p: Player = room.players.filter(user__user_id=data['user_id']).first()
        if p != None:

            # Kick if banned user
            if p.banned:
                self.kick()
                return

            # Handle requests for joined players
            if data['request_type'] == 'ping':
                self.ping(room, p)
            elif data['request_type'] == 'leave':
                self.leave(room, p)
            elif data['request_type'] == 'get_shown_question':
                self.get_shown_question(room)
            elif data['request_type'] == 'get_answer':
                self.get_answer(room)
            elif data['request_type'] == 'get_current_question_feedback':
                self.get_init_question_feedback(room, p)
            elif data['request_type'] == 'set_user_data':
                self.set_user_data(room, p, data['content'])
            elif data['request_type'] == 'next':
                self.next(room, p)
            elif data['request_type'] == 'buzz_init':
                self.buzz_init(room, p)
            elif data['request_type'] == 'buzz_answer':
                self.buzz_answer(room, p, data['content'])
            elif data['request_type'] == 'submit_initial_feedback':
                self.submit_initial_feedback(room, p, data['content'])
            elif data['request_type'] == 'submit_additional_feedback':
                self.submit_additional_feedback(room, p, data['content'])
            elif data['request_type'] == 'set_category':
                self.set_category(room, p, data['content'])
            elif data['request_type'] == 'set_difficulty':
                self.set_difficulty(room, p, data['content'])
            elif data['request_type'] == 'set_speed':
                self.set_speed(room, p, data['content'])
            elif data['request_type'] == 'reset_score':
                self.reset_score(room, p)
            elif data['request_type'] == 'chat':
                self.chat(room, p, data['content'])
            elif data['request_type'] == 'report_message':
                self.report_message(room, p, data['content'])
            else:
                pass

    def update_room(self, event):
        """Room update handler
        """
        self.send_json(event['data'])

    def ping(self, room, p):
        """Receive ping
        """

        p.last_seen = timezone.now().timestamp()
        p.save()

        update_time_state(room)

        self.send_json(get_room_response_json(room))
        self.send_json({
            'response_type': 'lock_out',
            'locked_out': p.locked_out,
        })

    def join(self, room: Room, data):
        """Join room
        """
        user = User.objects.filter(user_id=data['user_id']).first()
        if user == None:
            return

        # Create player if doesn't exist
        p = user.players.filter(room=room).first()

        # Get the players in the room that have last been seen within 10 seconds ago, excluding the user trying to join
        current_players = room.players.filter(
            Q(last_seen__gte=timezone.now().timestamp() - 10) &
            ~Q(user__user_id=data['user_id'])
        )

        if p == None and len(current_players) < room.max_players:
            p = Player.objects.create(room=room, user=user)
        
        if len(current_players) >= room.max_players:
            self.too_many_players()
        else:
            create_message("join", p, None, room)

            self.send_json(get_room_response_json(room))

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )

            if room.current_question:
                self.get_shown_question(room=room)
                self.get_answer(room=room)

    def leave(self, room, p):
        """Leave room
        """

        create_message("leave", p, None, room)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': get_room_response_json(room),
            }
        )

    def new_user(self, room):
        """Create new user and player in room
        """
        user = User.objects.create(user_id=generate_id(), name=generate_name())

        self.send_json({
            "response_type": "new_user",
            "user_id": user.user_id,
            "user_name": user.name,
        })

        return user

    def set_user_data(self, room, p, content):
        """Update player name
        """


        print(content)

        p.user.name = clean_content(content["user_name"])
        p.user.email = clean_content(content["user_email"])
        try:
            p.user.full_clean()
            p.user.save()

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )

        except ValidationError as e:
            return

    def next(self, room: Room, player: Player):
        """Next question
        """

        update_time_state(room)

        if room.state == 'idle':
            questions = (
                Question.objects.filter(difficulty=room.difficulty)
                if room.category == 'Everything'
                else Question.objects.filter(Q(category=room.category) & Q(difficulty=room.difficulty))
            )

            if room.collects_feedback:
                if room.current_question:
                    current_feedback = QuestionFeedback.objects.get(player=player, question=room.current_question)
                    
                    # Do not execute next if not finished with feedback
                    if not current_feedback.is_completed(): return

                # Get the IDs of questions with feedback from the player
                questions_ids_with_feedback = [feedback.question.question_id for feedback in player.feedback.all()]

                # Exclude questions with feedback from the player
                questions_without_feedback = Question.objects.exclude(question_id__in=questions_ids_with_feedback)
                questions = questions_without_feedback if len(questions_without_feedback) > 0 else questions

            # Abort if no questions
            if len(questions) <= 0:
                return

            q = random.choice(questions)

            room.state = 'playing'
            room.start_time = timezone.now().timestamp()
            room.end_time = room.start_time + (len(q.content.split())-1) / (room.speed / 60) # start_time (sec since epoch) + words in question / (words/sec)
            room.current_question = q

            room.save()

            # Unlock all players
            for p in room.players.all():
                p.locked_out = False
                p.save()

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )

    def buzz_init(self, room, p):
        """Initialize buzz
        """

        # Reject when not in contest
        if room.state != 'playing':
            return

        # Abort if no current question
        if room.current_question == None:
            return

        if not p.locked_out and room.state == 'playing':

            room.state = 'contest'
            room.buzz_player = p
            room.buzz_start_time = timezone.now().timestamp()
            room.save()

            p.locked_out = True
            p.save()

            create_message("buzz_init", p, None, room)

            self.send_json({
                'response_type': 'buzz_grant',
            })
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )

    def buzz_answer(self, room: Room, player: Player, content):

        # Reject when not in contest
        if room.state != 'contest':
            return

        # Abort if no buzz player or current question
        if room.buzz_player == None or room.current_question == None:
            return

        if player.player_id == room.buzz_player.player_id:

            cleaned_content = clean_content(content)
            answered_correctly: bool = judge_answer_annotation_game(cleaned_content,
                                                                    room.current_question.answer, 
                                                                    room.current_question.content,
                                                                    room.current_question.clue_list[-1])
            # answered_correctly: bool = judge_answer_kuiperbowl(cleaned_content, room.current_question.answer)
            words_to_show: int = self.compute_words_to_show(room)

            if answered_correctly:
                player.score += 10 # TODO: do not hardcode points
                player.correct += 1
                player.save()

                # Quick end question
                room.end_time = room.start_time
                room.state = Room.GameState.IDLE
                room.save()

                create_message(
                    "buzz_correct",
                    player,
                    cleaned_content,
                    room,
                )
            else:
                room.state = Room.GameState.PLAYING

                # Question reading ended, do penalty
                if room.end_time - room.buzz_start_time >= GRACE_TIME:
                    player.score -= 10
                    player.negs += 1
                    player.save()

                create_message(
                    "buzz_wrong",
                    player,
                    cleaned_content,
                    room,
                )

                self.send_json({
                    "response_type": "lock_out",
                    "locked_out": True,
                })

                buzz_duration = timezone.now().timestamp() - room.buzz_start_time
                room.start_time += buzz_duration
                room.end_time += buzz_duration
                room.save()

            current_question: Question = room.current_question
            try:
                feedback = QuestionFeedback.objects.get(question=current_question, player=player)
            except QuestionFeedback.DoesNotExist:
                feedback = QuestionFeedback.objects.create(
                    question=current_question,
                    player=player,
                    guessed_answer=cleaned_content,
                    guessed_generation_method='',
                    interestingness_rating=0,
                    submitted_clue_list=current_question.clue_list,
                    submitted_clue_order=list(range(current_question.length)),
                    submitted_factual_mask_list=[True] * current_question.length,
                    inversions=0,
                    feedback_text='',
                    improved_question='',
                    answered_correctly=answered_correctly,
                    buzz_position_word=words_to_show,
                    buzz_position_norm=words_to_show/len(current_question.content.split()),
                    buzzed=True
                )
                feedback.save()
            except ValidationError as e:
                pass

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )

        # Forfeit question if buzz time up
        elif timezone.now().timestamp() >= room.buzz_start_time + GRACE_TIME:
            buzz_duration = timezone.now().timestamp() - room.buzz_start_time
            room.state = 'playing'
            room.start_time += buzz_duration
            room.end_time += buzz_duration
            room.save()

            create_message(
                "buzz_forfeit",
                room.buzz_player,
                None,
                room,
            )

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )

    def submit_initial_feedback(self, room: Room, player: Player, content):
        if room.state == 'idle':
            try:
                current_question: Question = room.current_question
                feedback = QuestionFeedback.objects.get(question=current_question, player=player)
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
                        (not current_question.is_human_written and
                        feedback.guessed_generation_method == Question.GenerationMethod.AI)
                    )

                    feedback.save()
            except ValidationError as e:
                print(f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}")
            except KeyError as e:
                print(f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}")
                print(f"KeyError: {e}")
            
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': {
                        "response_type": "get_question_feedback",
                        "question_feedback": get_question_feedback_response_json(feedback),
                    },
                }
            )
    
    def submit_additional_feedback(self, room: Room, player: Player, content):
        if room.state == 'idle':
            try:
                current_question: Question = room.current_question
                feedback = QuestionFeedback.objects.get(question=current_question, player=player)
                if feedback.additional_submission_datetime is None:
                    feedback.submitted_clue_order = content['submitted_clue_order']
                    feedback.submitted_factual_mask_list = content['submitted_factual_mask_list']

                    # When counting inversions, we should ignore clues marked non-factual, since untrue things probably
                    # shouldn't have a "difficulty"
                    clue_order_for_factual_clues = list(filter(lambda i: feedback.submitted_factual_mask_list[i], feedback.submitted_clue_order))
                    feedback.inversions = count_inversions(clue_order_for_factual_clues)
                    feedback.submitted_clue_list = [current_question.clue_list[i] for i in feedback.submitted_clue_order]

                    feedback.improved_question = content['improved_question']
                    feedback.feedback_text = content['feedback_text']
                    feedback.additional_submission_datetime = timezone.now()
                    feedback.is_submitted = True

                    feedback.save()
            except ValidationError as e:
                print(f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}")
            except KeyError as e:
                print(f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}")
                print(f"KeyError: {e}")
            
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': {
                        "response_type": "get_question_feedback",
                        "question_feedback": get_question_feedback_response_json(feedback),
                    },
                }
            )


    def get_answer(self, room):
        """Get answer for room question
        """

        update_time_state(room)

        if room.state == 'idle':
            # Generate random question for now if empty
            if room.current_question == None:
                questions = Question.objects.all()

                # Abort if no questions
                if len(questions) <= 0:
                    return

                q = random.choice(questions)
                room.current_question = q
                room.save()

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': {
                        "response_type": "send_answer",
                        "answer": room.current_question.answer,
                    },
                }
            )
    
    def compute_words_to_show(self, room: Room) -> int:
        """Computes the number of words to show based on the elapsed time in the game."""
        current_time = timezone.now().timestamp()
        time_per_chunk = (60 / room.speed)

        if room.state == Room.GameState.IDLE:
            return len(room.current_question.content.split())
        elif room.state == Room.GameState.PLAYING:
            time_elapsed = current_time - room.start_time
        else:
            time_elapsed = room.buzz_start_time - room.start_time

        words_to_show = math.ceil(time_elapsed / time_per_chunk)
        return min(words_to_show, len(room.current_question.content.split()))

    def get_shown_question(self, room: Room):
        """Computes the correct amount of the question to show, depending on the state of the game.
            Note, this value is not persisted because, updating is too expensive."""
        shown_question = ""

        if room.current_question and room.current_question.content:
            full_question = room.current_question.content

            words_to_show = self.compute_words_to_show(room)
            shown_question = " ".join(full_question.split()[:words_to_show]) if (words_to_show > 0) else full_question
        
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': {
                    "response_type": "get_shown_question",
                    "shown_question": shown_question,
                },
            }
        )

    def get_init_question_feedback(self, room: Room, player: Player) -> None:
        """After a question is completed (i.e. the room becomes idle),
        send a message containing the feedback regarding the question"""

        # Cannot request during playing or contesting
        if room.state is Room.GameState.IDLE:
            return
        
        current_question: Question = room.current_question

        try:
            feedback = QuestionFeedback.objects.get(question=current_question, player=player)
        except QuestionFeedback.DoesNotExist:
            feedback = QuestionFeedback.objects.create(
                    question=current_question,
                    player=player,
                    guessed_generation_method='',
                    interestingness_rating=0,
                    submitted_clue_list=current_question.clue_list,
                    submitted_clue_order=list(range(current_question.length)),
                    submitted_factual_mask_list=[True] * current_question.length,
                    inversions=0,
                    feedback_text='',
                    improved_question='',
                    answered_correctly=False,
                    buzz_position_word=len(current_question.content.split()),
                    buzz_position_norm=1
                )
            feedback.save()
        except ValidationError as e:
            pass

        async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': {
                        "response_type": "get_question_feedback",
                        "question_feedback": get_question_feedback_response_json(feedback),
                    },
                }
            )

    def set_category(self, room, p, content):
        """Set room category
        """
        # Abort if change locked
        if room.change_locked:
            return

        try:
            room.category = clean_content(content)
            room.full_clean()
            room.save()

            create_message(
                "set_category",
                p,
                room.category,
                room,
            )
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )
        except ValidationError as e:
            pass

    def set_difficulty(self, room, p, content):
        """Set room difficulty
        """
        # Abort if change locked
        if room.change_locked:
            return

        try:
            room.difficulty = clean_content(content)
            room.full_clean()
            room.save()

            create_message(
                "set_difficulty",
                p,
                room.difficulty,
                room,
            )
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )
        except ValidationError as e:
            pass

    def set_speed(self, room, p, content):
        """Set room speed
        """
        # Abort if change locked

        try:
            room.speed = int(clean_content(content))
            room.full_clean()
            room.save()

            create_message(
                "set_speed",
                p,
                room.speed,
                room,
            )
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )
        except ValidationError as e:
            print(e)
            pass

    def reset_score(self, room, p):
        """Reset player score
        """

        p.score = 0
        p.save()

        create_message("reset_score", p, None, room)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': get_room_response_json(room),
            }
        )

    def chat(self, room, p, content):
        """ Send chat message
        """

        m = clean_content(content)

        create_message("chat", p, m, room)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': get_room_response_json(room),
            }
        )

    def kick(self):
        """Kick banned player
        """
        self.send_json({
            "response_type": "kick",
        })
        async_to_sync(self.channel_layer.group_discard)(
            self.room_name,
            self.channel_name
        )
    
    def too_many_players(self):
        """Too many players in a room. Cannot join room.
        """
        self.send_json({
            "response_type": "too_many_players",
        })
        async_to_sync(self.channel_layer.group_discard)(
            self.room_name,
            self.channel_name
        )

    def report_message(self, room, p, message_id):
        """Handle reporting messages
        """
        m = room.messages.filter(message_id=message_id).first()
        if m == None:
            return

        # Only report chat or buzz messages
        if m.tag == 'chat' or m.tag == 'buzz_correct' or m.tag == 'buzz_wrong':
            m.player.reported_by.add(p)
            m.save()

            # Ban if reported by 60% of players
            ratio = len(m.player.reported_by.all()) / len(room.players.all())
            if ratio > 0.6:
                m.player.banned = True
                m.player.save()

# === Helper methods ===

def update_time_state(room):

    """Checks time and updates state
    """
    if not room.state == 'contest':
        if timezone.now().timestamp() >= room.end_time + GRACE_TIME:
            room.state = 'idle'
            room.save()


def get_room_response_json(room):
    """Generates JSON for update response
    """

    return {
        "response_type": "update",
        "game_state": room.state,
        "current_time": timezone.now().timestamp(),
        "start_time": room.start_time,
        "end_time": room.end_time,
        "buzz_start_time": room.buzz_start_time,
        "category": room.current_question.category if room.current_question != None else "",
        "room_category": room.category,
        "messages": room.get_messages(),
        "difficulty": room.difficulty,
        "speed": room.speed,
        "players": room.get_players(),
        "change_locked": room.change_locked,
    }

def get_question_feedback_response_json(feedback: QuestionFeedback) -> Dict:
    # Serialize the feedback object to JSON
    feedback_json = serialize('json', [feedback])
    
    # Convert serialized data to dictionary
    feedback_dict = json.loads(feedback_json)[0]['fields']
    
    return feedback_dict

def create_message(tag, p, content, room):
    """Adds a message to db
    """
    try:
        m = Message(tag=tag, player=p, content=content, room=room)
        m.full_clean()
        m.save()
    except ValidationError as e:
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