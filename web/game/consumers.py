from typing import Dict, List
from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError
from django.db.models import Q
from channels.generic.websocket import JsonWebsocketConsumer

from django.core.serializers import serialize

from .models import *
from .utils import clean_content, generate_name, generate_id
from .judge import judge_answer_annotation_game

import json
import os
import datetime
import requests
from dotenv import load_dotenv
import math
import random
import logging
import justext
from bs4 import BeautifulSoup

load_dotenv()

logger = logging.getLogger('django')

GRACE_TIME = 3
INSTRUCTION_READING_TIME = 10
QUESTION_TIME = 10

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
        #print('receiving!', self.channel_layer)
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
        # Update connection if it's new
        if p.channel_name != self.channel_name:
            p.channel_name = self.channel_name
            p.save()

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
            elif data['request_type'] == 'get_answer':
                self.get_answer(room)
            # elif data['request_type'] == 'get_current_question_feedback':
            #     self.get_init_question_feedback(room, p)
            elif data['request_type'] == 'set_user_data':
                self.set_user_data(room, p, data['content'])
            elif data['request_type'] == 'next':
                self.next(room, p)
            elif data['request_type'] == 'skip':
                self.skip(room, p)
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
            elif data['request_type'] =='calculate':
                self.calculate(room, p, data['content'])
            elif data['request_type'] == 'web_search':
                self.web_search(room, p, data['content'])
            elif data['request_type'] == 'content_select':
                self.select_content(room, p, data['content'])
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
            # print(room.current_question)
            #if room.current_question:
            self.get_shown_question(room=room)
            self.get_answer(room=room)
            # else:
            #     self.handle_not_enough_players(room=room, send_alert=False)

            p.last_room = self.room_name

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

    def handle_not_enough_players(self, room: Room, send_alert: bool):
        
        # fetch a random question for a new room
        q = room.current_question
        if q == None:
            all_questions = Question.objects.all()
            if len(all_questions) <= 0:
                return
            q = random.choice(all_questions)

        q.content = 'Two players are needed to begin!'
        q.answer = ''
        room.current_question = q
        room.save()
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': get_room_response_json(room),
            }
        )
        if send_alert:
            self.send_json({
                "response_type": "not_enough_players",
            })
        self.get_shown_question(room=room)

    def next(self, room: Room, player: Player):
        """Next question
        """

        update_time_state(room)

        # transition so the user has time to read the instructions
        if room.state == Room.GameState.IDLE:
            players = room.get_players_by_score()
            num_players_in_room = len(players)

            # we need two players for a pairwise comparison
            if num_players_in_room != 2:
                self.handle_not_enough_players(room=room, send_alert=True)
                return

            # randomize player mappings
            p1, p2 = players
            if random.random() > 0.5:
                p1, p2 = p2, p1
            room.player_map = {str(p1['player_id']): 'A', str(p2['player_id']): 'B'}

            room.state = Room.GameState.INSTRUCTION_READING
            room.start_time = timezone.now().timestamp()
            room.end_time = room.start_time + INSTRUCTION_READING_TIME # (len(q.content.split())-1) / (room.speed / 60) # start_time (sec since epoch) + words in question / (words/sec)
            room.save()

            self.get_init_model_instructions(room=room)
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )
            self.get_shown_question(room=room)

        elif room.state == Room.GameState.INSTRUCTION_READING:

            questions = (
                Question.objects.filter(difficulty=room.difficulty)
                if room.category == 'Everything'
                else Question.objects.filter(Q(category=room.category) & Q(difficulty=room.difficulty))
            )

            # if room.collects_feedback:
            #     if room.current_question:
            #         current_feedback = QuestionFeedback.objects.get(player=player, question=room.current_question)
                    
            #         # Do not execute next if not finished with feedback
            #         #if not current_feedback.is_completed(): return

            #     # Get the IDs of questions with feedback from the player
            #     questions_ids_with_feedback = [feedback.question.question_id for feedback in player.feedback.all()]

            #     # Exclude questions with feedback from the player
            #     questions_without_feedback = (
            #         Question.objects.exclude(question_id__in=questions_ids_with_feedback)
            #         .filter(Q(category=room.category) & Q(difficulty=room.difficulty))
            #     )
            #     questions = questions_without_feedback if len(questions_without_feedback) > 0 else questions

            # Abort if no questions
            if len(questions) <= 0:
                return
            
            q = random.choice(questions)

            room.state = Room.GameState.PLAYING
            room.start_time = timezone.now().timestamp()
            room.end_time = room.start_time + QUESTION_TIME # (len(q.content.split())-1) / (room.speed / 60) # start_time (sec since epoch) + words in question / (words/sec)
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
            self.get_shown_question(room=room)

    def skip(self, room: Room, player: Player):
        """Skip question while it's playing.
        """
        current_question = room.current_question

        if room.state != Room.GameState.PLAYING or current_question == None:
            return
        
        if not player.locked_out and room.state == Room.GameState.PLAYING:
            # Quick end question
            room.end_time = room.start_time
            room.buzz_player = None
            room.state = Room.GameState.IDLE
            room.save()

            # try:
            #     feedback = QuestionFeedback.objects.get(question=current_question, player=player)
            # except QuestionFeedback.DoesNotExist:
            #     feedback = createFeedbackNoBuzz(room=room, player=player, skipped=True)
            #     feedback.save()
            # except ValidationError as e:
            #     pass

    def buzz_init(self, room: Room, p: Player):
        """Initialize buzz
        """

        # Reject when not in contest
        if room.state != Room.GameState.PLAYING:
            return

        # Abort if no current question
        if room.current_question == None:
            return

        if not p.locked_out and room.state == Room.GameState.PLAYING:

            room.state = Room.GameState.CONTEST
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
        if room.state != Room.GameState.CONTEST:
            return

        # Abort if no buzz player or current question
        if room.buzz_player == None or room.current_question == None:
            return

        if player.player_id == room.buzz_player.player_id:

            cleaned_content = clean_content(content)
            answered_correctly: bool = \
                judge_answer_annotation_game(cleaned_content, room.current_question)
            # answered_correctly: bool = judge_answer_kuiperbowl(cleaned_content, room.current_question.answer)
            words_to_show: int = room.compute_words_to_show()

            if answered_correctly:
                player.score += 10 # TODO: do not hardcode points
                player.correct += 1
                player.save()

                # Quick end question
                room.end_time = room.start_time
                room.buzz_player = None
                room.state = Room.GameState.IDLE
                room.save()

                create_message(
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
                room.save()

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
                    submitted_clue_list=current_question.clue_list,
                    submitted_clue_order=list(range(current_question.length)),
                    submitted_factual_mask_list=[0.5] * current_question.length,
                    answered_correctly=answered_correctly,
                    buzzed=True,
                    buzz_position_word=words_to_show,
                    buzz_position_norm=words_to_show/len(current_question.content.split()),
                    buzz_datetime=timezone.now()
                )
                feedback.save()
            except ValidationError as e:
                pass

            self.get_shown_question(room=room)

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
            room.state = Room.GameState.PLAYING
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
        if room.state == Room.GameState.IDLE:
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
        if room.state == Room.GameState.IDLE:
            try:
                current_question: Question = room.current_question
                feedback = QuestionFeedback.objects.get(question=current_question, player=player)
                if feedback.additional_submission_datetime is None:
                    feedback.submitted_clue_order = content['submitted_clue_order']
                    feedback.submitted_factual_mask_list = content['submitted_factual_mask_list']

                    # When counting inversions, we should ignore clues marked non-factual, since untrue things probably
                    # shouldn't have a "difficulty"
                    clue_order_for_factual_clues = list(filter(lambda i: feedback.submitted_factual_mask_list[i] >= 0.5, feedback.submitted_clue_order))
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

        if room.state == Room.GameState.IDLE:
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

    def get_shown_question(self, room: Room):
        """Computes the correct amount of the question to show, depending on the state of the game.
            Note, this value is not persisted because, updating is too expensive."""
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': {
                    "response_type": "get_shown_question",
                    "shown_question": room.get_shown_question(),
                    'state': room.state,
                },
            }
        )

    def get_init_model_instructions(self, room: Room) -> None:
        """After the players are ready for the next question, show them the right instructions"""

        if room.state != Room.GameState.INSTRUCTION_READING:
            return
        
        instruction_map = {'A': room.current_question.instructions_a, 'B': room.current_question.instructions_b}

        for player in room.get_valid_players():
            instruction_label = room.player_map[str(player.player_id)]
            instructions = instruction_map[instruction_label]         

            # Send instructions only to the player's WebSocket
            async_to_sync(self.channel_layer.send)(
                player.channel_name,  # Each player has their unique channel_name
                {
                    'type': 'update_room',
                    'data': {
                        'response_type': 'get_instructions',
                        'instructions': instructions,
                    }
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
            feedback = createFeedbackNoBuzz(room=room, player=player)
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

    def report_message(self, room: Room, p: Player, message_id):
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
            num_players_in_room = len(room.get_valid_players())
            ratio = len(m.player.reported_by.all()) / num_players_in_room
            if ratio > 0.6 and num_players_in_room > 1:
                m.player.banned = True
                m.player.save()

    def send_web_error(self, error=""):
        self.send(text_data=json.dumps({
            'response_type': 'web_search_result',
            'result': f"<p>No results found: {error}\nTry another search query!</p>"
        }))

    def web_search(self, room: Room, p: Player, query):

        api_key = os.getenv('GOOGLE_API_KEY')
        search_engine_id = os.getenv('GOOGLE_CSE_ID')
        google_search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": search_engine_id,
            "q": query,
            "num": 5,
        }

        search_results = None
        try:
            # return early if there are no web pages
            response = requests.get(google_search_url, params=params)
            response_data = response.json()
            search_results = response_data.get('items', [])
            if not search_results:
                self.send_web_error()
                return
        except Exception as e:
            self.send_web_error(str(e))

        # get all text from the top-5 web pages
        cand_paras = []
        for search_res in search_results:
            curr_link = search_res.get('link')
            curr_title = search_res.get('title')
            try:
                page_response = requests.get(curr_link, timeout=2)
            except Exception as e:
                cand_paras.append(('', []))
                continue
            if page_response.status_code != 200:
                cand_paras.append(('', []))
            else:
                paragraphs = justext.justext(page_response.content, justext.get_stoplist("English"))
                paragraphs = [p for p in paragraphs if not p.is_boilerplate]
                cand_paras.append((curr_title, paragraphs))

        # get the best web page (longest for now #TODO)
        title, paragraphs = max(cand_paras, key=lambda item: len(item[1]))
        print(cand_paras)
        print(paragraphs)
        if len(paragraphs) == 0:
            self.send_web_error()
            return 

        ALLOWED_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}

        result_string = f"<b>{title}</b> <hr />"
        for paragraph in paragraphs:
            if not paragraph.is_boilerplate:

                tag = paragraph.xpath.split('/')[-1]
                try:
                    tag = tag[:tag.index('[')]
                except ValueError:
                    pass
                if tag not in ALLOWED_TAGS:
                    tag = 'div'

                result_string += f'<{tag}>{paragraph.text}</{tag}>'

        print('Result:', result_string)

        # Send the extracted content back to the frontend
        self.send(text_data=json.dumps({
            'response_type': 'web_search_result',
            'result': result_string
        }))

    def select_content(self, room: Room, p: Player, equation):
        """Executes the content selection tool"""
        self.send(text_data=json.dumps({
            'response_type': 'content_selection_result',
            'result': 'Here is your selected content.'
        }))


    def calculate(self, room: Room, p: Player, equation):
        """Executes the calculator tool"""
        allowed_functions = {name: obj for name, obj in math.__dict__.items() if callable(obj)}

        allowed_functions.update({
            'abs': abs,
            'round': round,
        })

        try:
            result = eval(equation, {"__builtins__": None}, allowed_functions)

            self.send(text_data=json.dumps({
                'response_type': 'calculation_result',  # Identify the message type
                'result': result               # Send the calculated result
            }))
        
        except Exception as e:

            self.send(text_data=json.dumps({
                'response_type': 'calculation_result',  # Identify the message type
                'result': 'Invalid equation :('             # Send the calculated result
            }))



# === Helper methods ===

def update_time_state(room):

    """Checks time and updates state
    """
    if not room.state == Room.GameState.CONTEST:
        if timezone.now().timestamp() >= room.end_time:
            room.state = Room.GameState.IDLE
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
        "players": room.get_players_by_score(),
        "player_map": room.player_map,
        "change_locked": room.change_locked,
    }

def get_instructions_response_json(instructions: json) -> Dict:
    return dict(instructions)

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

def createFeedbackNoBuzz(room: Room, player: Player, skipped=False) -> QuestionFeedback:
    feedback = QuestionFeedback.objects.create(
        question=room.current_question,
        player=player,
        answered_correctly=False,
        skipped=skipped,
        buzzed=False,
        buzz_position_word=len(room.current_question.content.split()),
        buzz_position_norm=1,
        is_submitted = True,
        initial_submission_datetime=timezone.now()
    )
    return feedback

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