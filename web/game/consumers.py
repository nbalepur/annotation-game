from typing import Dict, List
from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError
from django.db.models import Q
from channels.generic.websocket import JsonWebsocketConsumer

from django.core.serializers import serialize

from .models import *
from .utils import clean_content, generate_name, generate_id
from .judge import judge_answer

import json
import os
import datetime
import nltk
import requests
from dotenv import load_dotenv
import math
import random
import logging
from bs4 import BeautifulSoup
import re
import cohere

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError

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

        """Websocket receive
        """

        data = json.loads(text_data)
        if 'content' not in data or data['content'] == None:
            data['content'] = ''

        room = Room.objects.get(label=self.room_name)

        print('receiving!', json.loads(text_data)['request_type'], room.state)

        #print('recieve', room.current_question, room.state)

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
                self.get_answer(room, player=p)
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
                self.select_content_wrapper(room, p, data['content'])
            else:
                pass

    def update_room(self, event):
        """Room update handler
        """
        self.send_json(event['data'])

    def ping(self, room, p):
        """Receive ping
        """

        print('ping', p)
        p.last_seen = timezone.now().timestamp()
        p.save()

        self.update_time_state(room, p)

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

        print('Current Players:', len(current_players))


        if p == None and len(current_players) < room.max_players:
            p = Player.objects.create(room=room, user=user)
        
        if len(current_players) >= room.max_players:
            self.too_many_players()
            print('too many!')
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
            room.refresh_from_db()
            # print(room.current_question)
            #if room.current_question:
            self.update_status(room, room.state)
            self.get_shown_question(room=room)
            self.get_answer(room=room, player=p)

            if room.state in {Room.GameState.PLAYING, Room.GameState.INSTRUCTION_READING}:
                self.update_tools_and_doc_for_question_and_player(room=room, player=p)
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
        if send_alert:
            self.send_json({
                "response_type": "not_enough_players",
            })

    def next(self, room: Room, player: Player):
        """Next question
        """
        # transition so the user has time to read the instructions
        if room.state == Room.GameState.IDLE:
            questions = Question.objects.filter(category=Question.Category.LONGCONTEXT)
            print(questions)
            if len(questions) <= 0:
                return
            # TODO: questions haven't seen before (when we have enough!)
            q = random.choice(questions)

            #print('changing question: expected')
            room.current_question = q
            room.state = Room.GameState.INSTRUCTION_READING
            room.start_time = timezone.now().timestamp()
            room.end_time = room.start_time + INSTRUCTION_READING_TIME # (len(q.content.split())-1) / (room.speed / 60) # start_time (sec since epoch) + words in question / (words/sec)
            room.save()
            self.update_status(room, room.state)

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            ) 
            
            self.get_init_model_instructions(room=room)
            self.show_and_disable_tools(room)
            self.get_shown_question(room=room)
                

        elif room.state == Room.GameState.INSTRUCTION_READING:
            
            room.state = Room.GameState.PLAYING
            room.start_time = timezone.now().timestamp()
            room.end_time = room.start_time + QUESTION_TIME # (len(q.content.split())-1) / (room.speed / 60) # start_time (sec since epoch) + words in question / (words/sec)
            room.save()

            # update status text
            self.update_status(room, room.state)

            # Unlock all players
            for p in room.players.all():
                p.locked_out = False
                p.save()

            for player in room.get_valid_players():
                self.disable_tool_btns(room=room, player=player, should_disable=False, should_clear_document=False)

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'update_room',
                    'data': get_room_response_json(room),
                }
            )

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
            self.update_status(room, room.state, p.user.name)

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

        self.log_tool_use(room, player, '', dict(), 'buzz', 'start')

        # Reject when not in contest
        if room.state != Room.GameState.CONTEST:
            return

        # Abort if no buzz player or current question
        if room.buzz_player == None or room.current_question == None:
            return

        if player.player_id == room.buzz_player.player_id:

            cleaned_content = clean_content(content)
            answered_correctly: bool = \
                judge_answer(cleaned_content, room.current_question)
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

                self.log_tool_use(room, player, '', dict(), 'buzz', 'success')
                self.update_status(room, 'buzz_correct', player.user.name, cleaned_content)
                self.log_leaderboard(room, player)
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

                self.log_tool_use(room, player, '', dict(), 'buzz', 'failure')
                self.update_status(room, 'buzz_incorrect', player.user.name, cleaned_content)

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

            self.log_tool_use(room, player, '', dict(), 'buzz', 'forfeit')
            self.update_status(room, 'buzz_abstain', player.user.name)

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


    def get_answer(self, room, player):
        """Get answer for room question
        """

        self.update_time_state(room, player)

        if room.state == Room.GameState.IDLE:
            # Generate random question for now if empty
            if room.current_question == None:
                questions = Question.objects.all()

                # Abort if no questions
                if len(questions) <= 0:
                    return

                q = random.choice(questions)
                q.answer = ''
                q.content = ''
                room.current_question = q
                room.save()

            # async_to_sync(self.channel_layer.group_send)(
            #     self.room_group_name,
            #     {
            #         'type': 'update_room',
            #         'data': {
            #             "response_type": "send_answer",
            #             "answer": room.current_question.answer,
            #         },
            #     }
            # )

    def get_shown_question(self, room: Room):
        """Computes the correct amount of the question to show, depending on the state of the game.
            Note, this value is not persisted because, updating is too expensive."""
        #print('shown', room.state, room.current_question)
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
            instruction_label = 'A'
            instructions = instruction_map[instruction_label]         

            # Send instructions only to the player's WebSocket
            async_to_sync(self.channel_layer.send)(
                player.channel_name,  # Each player has their unique channel_name
                {
                    'type': 'update_room',
                    'data': {
                        'response_type': 'update_instructions',
                        'instructions': instructions,
                    }
                }
            )
            self.log_tool_use(room, player, '', dict(), 'read_instructions', 'success')

    def update_tools_and_doc_for_question_and_player(self, room: Room, player: Player):
        """Update the visible tools and document based on the current question for just one player"""
        question = room.current_question    
        self.update_tools(self.channel_layer.send, player.channel_name, question.uses_calculator, (not question.uses_web_search and question.uses_doc_search), question.uses_web_search)
        curr_doc = '' if question.category != Question.Category.LONGCONTEXT else self.retrieve_from_document_cache('long_context:' + room.current_question.document_context)
        self.update_doc(self.channel_layer.send, player.channel_name, question.uses_doc_search, curr_doc)

    def show_and_disable_tools(self, room: Room):
        """Update the visible tools and document based on the current question"""
        for player in room.get_valid_players():     
            self.update_tools_and_doc_for_question_and_player(room=room, player=player)
            self.disable_tool_btns(room=room, player=player, should_disable=True, should_clear_document=room.current_question.uses_web_search)

    def update_status(self, room: Room, status: str, player_name='', answer=''):
        """Helper function to update the status text"""
        for player in room.get_valid_players():  
            async_to_sync(self.channel_layer.send)(
                player.channel_name,
                {
                    'type': 'update_room',
                    'data': {
                        'response_type': 'update_status',
                        'status': status,
                        'player': player_name,
                        'answer': answer,
                    }
                }
            )

    def disable_tool_btns(self, room: Room, player: Player, should_disable: bool, should_clear_document: bool):
        """Helper function to enable/disable the tool buttons"""
        async_to_sync(self.channel_layer.send)(
            player.channel_name,
            {
                'type': 'update_room',
                'data': {
                    'response_type': 'disable_tools',
                    'should_disable': should_disable,
                    'should_clear_document': should_clear_document,
                }
            }
        )

    def update_doc(self, channel_layer_send, player_channel, use_doc, doc_content):
        """Helper function to update document info"""
        async_to_sync(channel_layer_send)(
            player_channel,
            {
                'type': 'update_room',
                'data': {
                    'response_type': 'update_doc',
                    'use_doc': use_doc,
                    'doc_content': doc_content,
                }
            }
        )

    def update_tools(self, channel_layer_send, player_channel, use_calc, use_doc, use_web):
        """Helper function to update tool info"""
        async_to_sync(channel_layer_send)(
            player_channel,  # Each player has their unique channel_name
            {
                'type': 'update_room',
                'data': {
                    'response_type': 'update_tools',
                    'use_calculator': use_calc,
                    'use_doc': use_doc,
                    'use_web': use_web,
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

    def log_leaderboard(self, room: Room, p: Player):
        """Log the stats on this question for the leaderboard"""
        tool_calls = ToolLog.objects.filter(user_id=p.user.user_id, question_id=room.current_question.question_id).order_by('queried_at')
        num_buzzes = tool_calls.filter(tool_name="buzz").count()
        if num_buzzes == 0 or (num_buzzes == 4 and room.current_question.category == Question.Category.LONGCONTEXT):
            correctness = 0.0
        else:
            correctness = 1.0 / num_buzzes
        
        tool_calls = list(tool_calls)
        total_time_taken = (tool_calls[-1].queried_at - tool_calls[0].queried_at).total_seconds()
        if tool_calls[-1].tool_name == 'no_buzz':
            tool_calls_noninstruct = tool_calls[1:-1]
        else:
            tool_calls_noninstruct = tool_calls[1:]

        tool_runtime = 0
        for idx in range(len(tool_calls_noninstruct) // 2):
            tool_start, tool_end = tool_calls_noninstruct[2*idx], tool_calls_noninstruct[2*idx+1]
            print(tool_start.tool_name, tool_end.tool_name)
            print(tool_start.tool_execution_status, tool_end.tool_execution_status)
            # assert(tool_start.tool_name == tool_end.tool_name)
            # assert(tool_start.tool_execution_status == 'start')
            tool_runtime += (tool_end.queried_at - tool_start.queried_at).total_seconds() 

        LeaderboardLog.objects.create(
            user=p.user,
            question_id=room.current_question.question_id,
            correctness_score=correctness,
            seconds_taken=total_time_taken - tool_runtime
        )

    def log_tool_use(self, room: Room, p: Player, tool_query: str, tool_result: dict, tool_name: str, status: str):
        """Log the tool that was used"""
        ToolLog.objects.create(
            user_id=p.user.user_id,
            question_id=room.current_question.question_id,
            instruction_type='A',
            tool_name=tool_name,
            tool_query=tool_query,
            tool_result=tool_result,
            tool_execution_status=status
        )

    def send_web_search_error(self, room: Room, p: Player, query: str, error=""):
        """Handle errors during web search"""
        self.send(text_data=json.dumps({
            'response_type': 'web_search_result',
            'result': f"<p>No results found: {error}\nTry another search query!</p>"
        }))

        # log tool use
        self.log_tool_use(room, p, query, {'error': error}, 'web_search', 'failure')

    def retrieve_from_document_cache(self, key: str):
        doc_obj = Document.objects.filter(doc_id=key)
        if doc_obj.count() == 0:
            return None
        return doc_obj.first().document_text
    
    def add_to_document_cache(self, key: str, value: str):
        Document.objects.create(
            doc_id=key,
            document_text=value
        )

    def get_wiki_pages(self, room: Room, p: Player, query):
        """Get the Wikipedia page based on the query"""

        # # get Wikimedia token
        # session = self.scope["session"]
        # wikimedia_token = session.get('oauth_token')
        # oauth_session = OAuth2Session(os.getenv('WIKIMEDIA_CLIENT_ID'), token=wikimedia_token)

        # api_url = 'https://en.wikipedia.org/w/api.php'
        # params = {
        #     "action": "opensearch",
        #     "search": '+'.join(query.lower().split()),
        #     "limit": 5,
        #     "namespace": 0,
        #     "format": "json",
        # }

        # try:
        #     response = oauth_session.get(api_url, params=params)
        # except TokenExpiredError:
        #     print('expired!')
        #     self.send(text_data=json.dumps({
        #         'response_type': 'reauthenticate',
        #     }))
        #     self.close()
        #     return
        # except Exception as e:
        #     self.send_web_search_error(room, p, query, str(e))
            
        # if response.status_code == 200:
        #     data = response.json()
        #     search_results = data[1]
        # else:
        #     self.send_web_search_error(room, p, query, f'Error Code: {response.status_code}')
        #     return

        # get text from the Wikipedia page

        query = self.clean_query(query)
        self.log_tool_use(room, p, query, dict(), 'web_search', 'start')

        cached_query_res = self.retrieve_from_document_cache('wiki_title_query:' + query)
        if cached_query_res != None:
            return [cached_query_res], 'from_cache'

        try:
            api_key = os.getenv('GOOGLE_API_KEY')
            search_engine_id = os.getenv('GOOGLE_CSE_ID')
            google_search_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": api_key,
                "cx": search_engine_id,
                "q": query,
                "num": 10,
            }
            response = requests.get(google_search_url, params=params)
            response_data = response.json()
            search_results = response_data.get('items', [])
            if not search_results:
                return ['no_search_results'], 'error'
        except Exception as e:
            return [str(e)], 'error'

        return [r['title'].replace(' - Wikipedia', '').strip() for r in search_results], 'new_search'

    def extract_elements_from_html(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        elements = soup.find_all(id=re.compile(r'^element-'))
        sentences = []
        for elem in elements:
            sentences.append(elem.text.strip())
        return sentences

    def send_web_search_success(self, room: Room, p: Player, query: str, title: str, final_html: str, cache_title: bool, cache_html: bool):
        """Successful web search"""

        if cache_title:
            self.add_to_document_cache('wiki_title_query:' + query, title)
        if cache_html:
            self.add_to_document_cache('wiki_page_query:' + title, final_html)

        self.log_tool_use(room, p, query, title, 'web_search', 'success')
        self.send(text_data=json.dumps({
            'response_type': 'web_search_result',
            'result': final_html
        }))
        self.update_tools(self.channel_layer.send, p.channel_name, room.current_question.uses_calculator, True, True)

        # auto-search for the relevant paragraph
        self.select_content(room, p, query, final_html)

    def web_search(self, room: Room, p: Player, query):

        wiki_pages, status = self.get_wiki_pages(room, p, query)
        print(wiki_pages, status)
        if status == 'error':
            self.send_web_search_error(room, p, query, wiki_pages[0])
            return

        session = self.scope["session"]
        wikimedia_token = session.get('oauth_token')
        oauth_session = OAuth2Session(os.getenv('WIKIMEDIA_CLIENT_ID'), token=wikimedia_token)
        
        for page_title in wiki_pages:
            page_title_clean = self.clean_query(page_title)

            cached_page_res = self.retrieve_from_document_cache('wiki_page_query:' + page_title_clean)

            if cached_page_res != None:
                print('page found in cache!')
                self.send_web_search_success(room=room,
                                    p=p,
                                    query=self.clean_query(query),
                                    title=page_title_clean,
                                    final_html=cached_page_res,
                                    cache_title=(status == 'new_search'),
                                    cache_html=False)
                return
            
            print('page not found')
        
            params = {
                "action": "parse",
                "page": page_title,
                "format": "json",
                "prop": "text|images",
                "redirects": 1,
            }

            try:
                api_url = 'https://en.wikipedia.org/w/api.php'
                response = oauth_session.get(api_url, params=params)
            except TokenExpiredError:
                self.send(text_data=json.dumps({
                    'response_type': 'reauthenticate',
                }))
                self.close()
                return
            except Exception as e:
                continue
            
            if response.status_code == 200:
                data = response.json()
                html_content = data["parse"]["text"]["*"]
                title = data["parse"]["title"]
                soup = BeautifulSoup(html_content, 'html.parser')
                
                element_counter = 0

                # TODO: fix the web scraping
            
                for p_tag in soup.find_all('p'):
                    text = p_tag.get_text()
                    if text:
                        p_tag['id'] = f"element-{element_counter}"
                        element_counter += 1
                
                # for li_tag in soup.find_all('li'):
                #     if not (li_tag.a and len(li_tag.contents) == 1):
                #         text = li_tag.get_text()
                #         if text:
                #             content_list.append(text)
                #             li_tag['id'] = f"element-{element_counter}"
                #             element_counter += 1
                
                fixed_html_content = str(soup)
                openbracket, closebracket = '{', '}'
                wikipedia_css = '''
                <link rel="stylesheet" href="https://en.wikipedia.org/w/load.php?debug=false&lang=en&modules=mediawiki.legacy.shared|mediawiki.skinning.content|mediawiki.skinning.interface&only=styles&skin=vector">
                <link rel="stylesheet" href="https://en.wikipedia.org/w/load.php?debug=false&lang=en&modules=site.styles&only=styles&skin=vector">
                '''
        #         copy_script = '''<script>
        #     document.addEventListener("keydown", function(e) {
        #       if ((e.ctrlKey || e.metaKey) && e.key == "c") {
        #         navigator.clipboard.readText()
        #         .then(text => {
        #           window.parent.sendToNotes(text);
        #         })
        #         .catch(err => {
        #           console.error("Error reading clipboard contents:", err);
        #         });
        #       }
        #     });
        #   </script>'''
                copy_script = ''
                final_html = f'''
                <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{title}</title>
                    {wikipedia_css}
                    <style>
                        a {openbracket}
                            pointer-events: none;
                        {closebracket}
                        .highlight {openbracket}
                            background-color: yellow; /* Color for the highlight */
                            transition: background-color 1s ease; /* Smooth transition */
                        {closebracket}
                        body {openbracket}
                        font-size: 1.2em; /* Scale up text size by 20% */
                        {closebracket}
                    </style>
                </head>
                <body>
                    <div class="mw-body-content">
                        <div class="page-header">
                            <h1>{title.replace("_", " ")}</h1>
                        </div>
                        {fixed_html_content}
                    </div>
                    {copy_script}
                </body>
                </html>
                '''
                print('new page')
                self.send_web_search_success(room=room,
                                             p=p,
                                             query=self.clean_query(query),
                                             title=page_title_clean,
                                             final_html=final_html,
                                             cache_title=(status == 'new_search'),
                                             cache_html=True)

                return
            else:
                continue
        
        self.send_web_search_error(room, p, query, 'no_page_content')

    def clean_query(self, query):
        cleaned_query = re.sub(r'[^a-zA-Z0-9\s\-]', '', query)
        cleaned_query = re.sub(r'\s+', '-', cleaned_query.strip())
        return cleaned_query.lower()

    def select_content_wrapper(self, room: Room, p: Player, query: str):
        html = self.retrieve_from_document_cache('long_context:' + room.current_question.document_context)
        print('got the doc!')
        self.select_content(room, p, query, html)

    def select_content(self, room: Room, p: Player, query: str, html: str):
        """Executes the content selection tool"""

        self.log_tool_use(room, p, query, dict(), 'content_selection', 'start')
        docs = self.extract_elements_from_html(html)

        cohere_client = cohere.ClientV2(api_key=os.getenv('COHERE_API_KEY'))

        try:
            retr_results = cohere_client.rerank(model="rerank-english-v3.0", query=query, documents=docs, top_n=1, return_documents=True)
        except Exception as e:
            self.send(text_data=json.dumps({
                'response_type': 'content_selection_result',
                'result': [],
            }))
            self.log_tool_use(room, p, query, {'error': str(e)}, 'content_selection', 'failure')
            return

        retr_docs = [d.document.text for d in retr_results.results]
        retr_docs = [re.sub(r'\[.*?\]', ' ', doc) for doc in retr_docs]
        retr_docs = [re.sub(r'\s+', ' ', doc).strip() for doc in retr_docs]
        doc_idxs = [int(d.index) for d in retr_results.results]

        self.log_tool_use(room, p, query, {'retrieved_docs': retr_docs, 'doc_idxs': doc_idxs}, 'content_selection', 'success')

        # Send the retrieved content back to the frontend
        self.send(text_data=json.dumps({
            'response_type': 'content_selection_result',
            'result': doc_idxs,
            'num_docs': len(docs),
        }))

    def calculate(self, room: Room, p: Player, equation):
        """Executes the calculator tool"""
        self.log_tool_use(room, p, equation, dict(), 'calculator', 'start')
        allowed_functions = {name: obj for name, obj in math.__dict__.items() if callable(obj)}
        allowed_functions.update({
            'abs': abs,
            'round': round,
        })

        try:
            result = eval(equation, {"__builtins__": None}, allowed_functions)

            # log tool use
            self.log_tool_use(room, p, equation, {'calculation': result}, 'calculator', 'success')

            self.send(text_data=json.dumps({
                'response_type': 'calculation_result',  # Identify the message type
                'result': result               # Send the calculated result
            }))
        
        except Exception as e:

            # log tool use
            self.log_tool_use(room, p, equation, {'error': str(e)}, 'calculator', 'failure')

            self.send(text_data=json.dumps({
                'response_type': 'calculation_result',  # Identify the message type
                'result': 'ERROR'             # Send the calculated result
            }))
            

    # === Helper methods ===

    def update_time_state(self, room: Room, player: Player):

        """Checks time and updates state
        """
        if not room.state == Room.GameState.CONTEST:
            if timezone.now().timestamp() >= room.end_time and room.state != Room.GameState.IDLE:
                room.state = Room.GameState.IDLE
                curr_answer = room.current_question.answer_accept[0]
                room.save()
                self.update_status(room, room.state, '', curr_answer)
                self.log_leaderboard(room, player)
                self.log_tool_use(room, player, '', dict(), 'no_buzz', 'start')

                # for player in room.get_valid_players():
                #     self.disable_tool_btns(room=room, player=player)

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