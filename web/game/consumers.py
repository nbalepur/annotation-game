from typing import Dict, List
from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from channels.generic.websocket import JsonWebsocketConsumer

from django.core.serializers import serialize
from django.shortcuts import redirect

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

from sympy import sqrt, Abs, pi
from sympy.core.sympify import SympifyError
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

load_dotenv()

logger = logging.getLogger("django")

GRACE_TIME = 3
INSTRUCTION_READING_TIME = 10
QUESTION_TIME = 10


class QuizbowlConsumer(JsonWebsocketConsumer):
    """Websocket consumer for quizbowl game"""

    def connect(self):
        """Websocket connect"""
        self.room_name = self.scope["url_route"]["kwargs"]["label"]
        self.room_group_name = f"game-{self.room_name}"

        # Validate user session
        self.user_id = self.scope["session"].get("user_id")
        if not self.user_id:
            self.close()  # Close WebSocket connection for unauthenticated users
            return

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        """Websocket disconnect"""
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    def receive(self, text_data):
        """Websocket receive"""

        data = json.loads(text_data)
        if "content" not in data or data["content"] == None:
            data["content"] = ""

        # ensure the session is still valid
        session_user_id = self.scope["session"].get("user_id")
        if not session_user_id or session_user_id != self.user_id:
            self.close()
            return
        
        room = Room.objects.get(label=self.room_name)
        
        if data["request_type"] == "new_user":
            user = self.new_user()
            data["user_id"] = user.user_id
            self.join(room, data)

        if "user_id" not in data or "request_type" not in data:
            return
        if len(User.objects.filter(user_id=data["user_id"])) <= 0:
            user = self.new_user()
            data["user_id"] = user.user_id

        # Handle join
        if data["request_type"] == "join":
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
            if data["request_type"] == "ping":
                self.ping(room, p)
            elif data["request_type"] == "leave":
                self.leave(room, p)
            elif data["request_type"] == "get_answer":
                self.get_answer(room, player=p)
            # elif data['request_type'] == 'get_current_question_feedback':
            #     self.get_init_question_feedback(room, p)
            elif data["request_type"] == "set_user_data":
                self.set_user_data(room, p, data["content"])
            elif data["request_type"] == "next":
                self.next(room, p)
            elif data["request_type"] == "skip":
                self.skip(room, p)
            elif data["request_type"] == "show_next_step":
                self.show_next_step(room=room, player=p, subanswers=data["content"])
            elif data["request_type"] == "swap_plan":
                self.swap_plan(room=room, player=p, subanswers=data["content"])
            elif data["request_type"] == "send_subanswers":
                self.send_subanswers(
                    room=room,
                    player=p,
                    subanswers=data["content"]["subanswers"],
                    is_correct=data["content"]["is_correct"],
                    is_final=data["content"]["is_final"],
                    followed_plan=data["content"]["followed_plan"],
                    notes=data["content"]["notes"]
                )
            elif data["request_type"] == "buzz_init":
                self.buzz_init(room, p, data["content"])
            elif data["request_type"] == "buzz_answer":
                self.buzz_answer(room, p, data["content"])
            elif data["request_type"] == "no_buzz":
                self.handle_no_buzz(room, p, False)
            elif data["request_type"] == "submit_initial_feedback":
                self.submit_initial_feedback(room, p, data["content"])
            elif data["request_type"] == "submit_additional_feedback":
                self.submit_additional_feedback(room, p, data["content"])
            elif data["request_type"] == "set_category":
                self.set_category(room, p, data["content"])
            elif data["request_type"] == "set_difficulty":
                self.set_difficulty(room, p, data["content"])
            elif data["request_type"] == "set_speed":
                self.set_speed(room, p, data["content"])
            elif data["request_type"] == "reset_score":
                self.reset_score(room, p)
            elif data["request_type"] == "chat":
                self.chat(room, p, data["content"])
            elif data["request_type"] == "report_message":
                self.report_message(room, p, data["content"])
            elif data["request_type"] == "report_issue":
                self.report_issue(room, p, data["content"])
            elif data["request_type"] == "calculate":
                self.calculate(room, p, data["content"])
            elif data["request_type"] == "web_search":
                self.web_search(room, p, data["content"])
            elif data["request_type"] == "content_select":
                self.select_content_wrapper(room, p, data["content"])
            elif data["request_type"] == "log_comparison":
                self.log_comparison(room, p, data["content"])
            elif data["request_type"] == "decrease_steps":
                self.decrease_steps(room, p, data['content'])
            elif data["request_type"] == "change_category":
                self.change_category(room, p, data['content'])
            else:
                pass

    def update_room(self, event):
        """Room update handler"""
        self.send_json(event["data"])

    def ping(self, room, p):
        """Receive ping"""

        print("ping", p)
        p.last_seen = timezone.now().timestamp()
        p.save()

        self.update_time_state(room, p)

        self.send_json(get_room_response_json(room))
        self.send_json(
            {
                "response_type": "lock_out",
                "locked_out": p.locked_out,
            }
        )

    def change_category(self, room: Room, player: Player, category: str):
        category_map = {
            'Everything': Question.Category.EVERYTHING,
            'Math': Question.Category.MATH,
            'Trivia': Question.Category.MULTIHOP
        }
        
        user = player.user
        user.category_preference = category_map[category]
        user.save()

        room.category = category_map[category]
        room.save()
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": get_room_response_json(room),
            },
        )

    def join(self, room: Room, data):
        """Join room"""
        user = User.objects.filter(user_id=data["user_id"]).first()
        if user == None:
            print("No user found!")
            return
        if user.experiment_group == None:
            print("No experiment group found!")
            return
        
        # pass the experiment group to the front-end
        self.update_experiment_type(user)
        
        room.steps_seen_a = 1
        room.steps_seen_b = 1
        room.curr_instructions_letter = None
        room.curr_subanswers_a = None
        room.curr_subanswers_b = None

        room.category = user.category_preference

        # Create player if doesn't exist
        p = user.players.filter(room=room).first()

        # Get the players in the room that have last been seen within 10 seconds ago, excluding the user trying to join
        current_players = room.players.filter(
            Q(last_seen__gte=timezone.now().timestamp() - 10)
            & ~Q(user__user_id=data["user_id"])
        )

        if p == None and len(current_players) < room.max_players:
            p = Player.objects.create(room=room, user=user)

        if len(current_players) >= room.max_players:
            self.too_many_players()
            print("too many!")
        else:
            create_message("join", p, None, room)

            room.state = Room.GameState.IDLE
            self.send_json(get_room_response_json(room))
            room.save()

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    "type": "update_room",
                    "data": get_room_response_json(room),
                },
            )

            room.refresh_from_db()
            self.update_status(room, room.state, p)
            self.show_and_disable_tools(room=room, player=p)

            p.last_room = self.room_name

    def leave(self, room, p):
        """Leave room"""
        create_message("leave", p, None, room)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": get_room_response_json(room),
            },
        )

    def decide_expt_group(self, user: User):

        if user.experiment_group is not None:
            return user.experiment_group
        
        # (question_id, did_comparison) -> number of users who have done it
        question_user_count = (
            AnswerData.objects.filter(followed_plan=True, is_final=True, is_report=False)
            .values("question_id", "did_comparison")
            .annotate(user_count=Count("user__user_id", distinct=True))
        )
        question_to_user_count = {
            (entry["question_id"], entry["did_comparison"]): entry["user_count"]
            for entry in question_user_count
        }

        num_swap_questions_done = 0
        num_pairwise_questions_done = 0
        for k, v in question_to_user_count.items():
            if k[1]:
                num_pairwise_questions_done += int(v >= 6)
            else:
                num_swap_questions_done += int(v >= 3)
        
        num_swap_users = len(User.objects.filter(experiment_group=User.ExperimentGroup.SWAP))
        num_pairwise_users = len(User.objects.filter(experiment_group=User.ExperimentGroup.PAIRWISE))

        if num_swap_questions_done == num_pairwise_questions_done:
            if num_swap_users < num_pairwise_users:
                return User.ExperimentGroup.SWAP
            elif num_pairwise_users < num_swap_users:
                return User.ExperimentGroup.PAIRWISE
            else:
                return User.ExperimentGroup.PAIRWISE if random.uniform(0, 1) > 0.5 else User.ExperimentGroup.SWAP
        elif num_swap_questions_done > num_pairwise_questions_done:
            return User.ExperimentGroup.PAIRWISE
        else:
            return User.ExperimentGroup.SWAP

    def new_user(self):
        """Create new user and player in room"""
        user = User.objects.filter(user_id=self.user_id).first()
        expt_group = self.decide_expt_group(user)
        user.experiment_group = expt_group
        user.save()
        self.send_json(
            {
                "response_type": "new_user",
                "user_id": user.user_id,
                "user_name": user.name,
                "user_email": user.email,
            }
        )

        return user
    
    def check_duplicate_user_data(self, adj_username, adj_email):
        """Check if there's duplicate information in the user data"""
        print('adjusted:', adj_username, adj_email)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "check_duplicate_user_data",
                    "username": adj_username,
                    "email": adj_email,
                },
            },
        )
        pass

    def set_user_data(self, room: Room, p: Player, content):
        """Update player name"""

        # get the current owner of the user names + emails
        old_user_name = clean_content(content["user_name"])
        old_email = clean_content(content["user_email"])

        curr_username_user = User.objects.filter(name=old_user_name)
        curr_email_user = User.objects.filter(email=old_email)

        # check if these are valid to use: if no one exists, or if it's the current user
        username_is_valid = (not curr_username_user.exists()) or (curr_username_user.first().user_id == p.user.user_id)
        email_is_valid = (not curr_email_user.exists()) or (curr_email_user.first().user_id == p.user.user_id)

        # set the new values accordingly
        new_user_name = old_user_name if username_is_valid else ''
        new_email = old_email if email_is_valid else ''

        self.check_duplicate_user_data(new_user_name, new_email)

        if username_is_valid or email_is_valid:

            p.user.name = new_user_name
            p.user.email = new_email

            try:
                p.user.full_clean()
                p.user.save()

                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        "type": "update_room",
                        "data": get_room_response_json(room),
                    },
                )
            except ValidationError as e:
                return

    def handle_not_enough_players(self, room: Room, send_alert: bool):
        """Logic to run when there's not enough players"""

        if send_alert:
            self.send_json(
                {
                    "response_type": "not_enough_players",
                }
            )

    def transition_to_instruction(self, room: Room, player: Player):
        """Logic for the transition state to instruction reading"""

        room.state = Room.GameState.INSTRUCTION_READING
        room.start_time = timezone.now().timestamp()
        room.end_time = (
            room.start_time + INSTRUCTION_READING_TIME
        )  # (len(q.content.split())-1) / (room.speed / 60) # start_time (sec since epoch) + words in question / (words/sec)
        room.save()
        self.update_status(room, room.state, player)

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": get_room_response_json(room),
            },
        )

        self.get_init_model_instructions(room=room, player=player, should_clear=True, num_steps=-1)
        #self.clear_instructions(room=room, player=player)
        self.show_and_disable_tools(room=room, player=player)
        self.disable_plan()

        self.log_tool_use(room, player, "", dict(), "read_instructions", "start")

    def populate_comparison_pane(self, room: Room):
        """Populate visible information in the comparison pane"""
        q = room.current_question

        q_text = q.content
        instr_a = q.instructions_a
        instr_b = q.instructions_b
        swapped = False
        if random.uniform(0, 1) > 0.5:  # account for position biases
            instr_a, instr_b = instr_b, instr_a
            swapped = True

        instruction_map = {"A": instr_a, "B": instr_b, "swapped": swapped}
        room.instruction_map = instruction_map
        room.save()
        room.refresh_from_db()

        # print(instr_a, instr_b)

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "populate_comparison",
                    "question": q_text,
                    "instructions_a": instr_a,
                    "instructions_b": instr_b,
                },
            },
        )
        pass

    def toggle_comparison_visibility(self, room: Room, show_comparison: bool):
        """Toggle the visibility of the comparison pane"""
        if show_comparison:
            self.populate_comparison_pane(room)

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "toggle_comparison",
                    "show_comparison": show_comparison,
                },
            },
        )

    def decide_question_category(self, player: Player):

        # find the unseen math questions
        all_questions_math = Question.objects.filter(
            Q(category=Question.Category.MATH) & (
                Q(generation_method=Question.GenerationMethod.LLAMA) |
                Q(generation_method=Question.GenerationMethod.QWEN)
            )
        )
        seen_questions_overall_math = AnswerData.objects.filter(
            user=player.user, category=Question.Category.MATH
        ).values_list("question_id", flat=True)
        unseen_questions_math = all_questions_math.exclude(
            question_id__in=seen_questions_overall_math
        )

        # find the unseen trivia questions
        all_questions_trivia = Question.objects.filter(
            Q(category=Question.Category.MULTIHOP) & (
                Q(generation_method=Question.GenerationMethod.LLAMA) |
                Q(generation_method=Question.GenerationMethod.QWEN)
            )
        )
        seen_questions_overall_trivia = AnswerData.objects.filter(
            user=player.user, category=Question.Category.MULTIHOP
        ).values_list("question_id", flat=True)
        unseen_questions_trivia = all_questions_trivia.exclude(
            question_id__in=seen_questions_overall_trivia
        )

        # decide which question to show
        if len(unseen_questions_math) + len(unseen_questions_trivia) == 0:
            return Question.Category.MULTIHOP if random.uniform(0, 1) > 0.5 else Question.Category.MATH # pick randomly if no more questions
        if len(unseen_questions_math) == 0:
            return Question.Category.MULTIHOP # pick trivia if no more math questions
        if len(unseen_questions_trivia) == 0:
            return Question.Category.MATH # pick math if no more trivia questions
        
        return Question.Category.MULTIHOP if random.uniform(0, 1) > 0.5 else Question.Category.MATH # random selection otherwise
        

    def decide_next_question(
        self, room: Room, player: Player, category: Question.Category, is_comparison: bool
    ):
        
        # if either category can be shown, decide what the next one should be
        if category == Question.Category.EVERYTHING:
            category = self.decide_question_category(player)

        # (question_id, did_comparison) -> number of users who have done it
        question_user_count = (
            AnswerData.objects.filter(followed_plan=True, is_final=True, is_report=False)
            .values("question_id", "did_comparison")
            .annotate(user_count=Count("user__user_id", distinct=True))
        )
        question_to_user_count = {
            (entry["question_id"], entry["did_comparison"]): entry["user_count"]
            for entry in question_user_count
        }

        # questions the user has already seen for this category and experimental group
        seen_questions = AnswerData.objects.filter(
            user=player.user, category=category, did_comparison=is_comparison
        ).values_list("question_id", flat=True)

        # questions the user has seen overall
        seen_questions_overall = AnswerData.objects.filter(
            user=player.user, category=category
        ).values_list("question_id", flat=True)

        # check if we need to give a tutorial question or an attention check question
        if len(seen_questions) == int(os.getenv("NUM_SEEN_FOR_TUTORIAL")):
            return Question.objects.filter(category=category, generation_method=Question.GenerationMethod.TUTORIAL).first()
        elif len(seen_questions) == int(os.getenv("NUM_SEEN_FOR_ATTENTION")) + 1: # account for the extra question seen as the tutorial question
            attention_type = Question.GenerationMethod.ATTENTION_PAIRWISE if is_comparison else Question.GenerationMethod.ATTENTION_SWAP
            return Question.objects.filter(category=category, generation_method=attention_type).first()

        # otherwise, get the questions that have not been seen
        all_questions = Question.objects.filter(
            Q(category=category) & (
                Q(generation_method=Question.GenerationMethod.LLAMA) |
                Q(generation_method=Question.GenerationMethod.QWEN)
            )
        )
        unseen_questions = all_questions.exclude(
            question_id__in=seen_questions_overall # ignore questions the user may have encountered in either section
        )

        # determine the question limit: for swapping, we need 3 annotations. for pairwise, we need 6 annotations (3 on plan A, 3 on plan B)
        NUM_QUESTIONS_NEEDED = 6 if is_comparison else 3

        # find the questions that almost have this number of annotators
        filtered_questions = [
            question
            for question in unseen_questions
            if question_to_user_count.get((question.question_id, is_comparison), 0) < NUM_QUESTIONS_NEEDED
        ]
        filtered_questions.sort(
            key=lambda q: abs(NUM_QUESTIONS_NEEDED - question_to_user_count.get((q.question_id, is_comparison), 0))
        )

        # if all questions have been annotated
        if len(filtered_questions) == 0:
            if unseen_questions.count() == 0:
                q = random.choice(all_questions) # if the user has seen all questions, give them one they have already seen
                return q
            else:
                q = random.choice(unseen_questions) # if there are still some left, pick one of those
            return q

        return filtered_questions[0] # return the question closest to being fully annotated
    
    def next(self, room: Room, player: Player):
        """Next question"""
        # transition so the user has time to read the instructions
        if room.state == Room.GameState.IDLE:

            question_type = room.category
            q = self.decide_next_question(
                room=room, player=player, 
                category=question_type, 
                is_comparison=player.user.experiment_group == User.ExperimentGroup.PAIRWISE
            )
            if q == None:  # no questions available D:
                return
            room.current_question = q
            # display the question now that we have one
            self.get_shown_question(room=room)

            room.steps_seen_a = 1
            room.steps_seen_b = 1
            room.curr_instructions_letter = None
            room.curr_subanswers_a = None
            room.curr_subanswers_b = None
            room.last_guess = None
            self.load_instructions(room=room, player=player)

            # get this logging party started
            self.log_tool_use(room, player, "", dict(), "question", "start")

            show_comparisons_before = (player.user.experiment_group == User.ExperimentGroup.PAIRWISE)
            room.show_comparisons_before = show_comparisons_before

            if show_comparisons_before:
                room.state = Room.GameState.PAIRWISE_COMPARISON
                room.save()
                self.update_status(room, room.state, player)
                self.toggle_comparison_visibility(room=room, show_comparison=True)
                self.log_tool_use(room, player, "", dict(), "pairwise_comparison", "start")
            else:
                self.transition_to_instruction(room, player)

        elif room.state in {Room.GameState.INSTRUCTION_READING}:

            room.state = Room.GameState.PLAYING
            room.start_time = timezone.now().timestamp()
            room.end_time = (
                room.start_time + QUESTION_TIME
            )  # (len(q.content.split())-1) / (room.speed / 60) # start_time (sec since epoch) + words in question / (words/sec)
            steps_seen = (
                room.steps_seen_a
                if room.curr_instructions_letter == "A"
                else room.steps_seen_b
            )
            self.get_init_model_instructions(
                room=room,
                player=player,
                num_steps=steps_seen,
                should_clear=(steps_seen == 1),
            )
            room.save()

            # update status text
            self.update_status(room, room.state, player)

            # Unlock all players
            for p in room.players.all():
                p.locked_out = False
                p.save()

            self.disable_tool_btns(
                room=room,
                player=player,
                should_disable=False,
                should_clear_document=False,
            )

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    "type": "update_room",
                    "data": get_room_response_json(room),
                },
            )

            self.log_tool_use(room, p, "", dict(), 
                              "pairwise_comparison" if room.show_comparisons_before else "read_instructions", 
                              "success")

    def skip(self, room: Room, player: Player):
        """Skip question while it's playing."""
        current_question = room.current_question

        if room.state != Room.GameState.PLAYING or current_question == None:
            return

        if not player.locked_out and room.state == Room.GameState.PLAYING:
            # Quick end question
            room.end_time = room.start_time
            room.buzz_player = None
            room.state = Room.GameState.IDLE
            room.save()

    def buzz_init(self, room: Room, p: Player, guess: str):
        """Initialize buzz"""

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
            self.update_status(room, room.state, p)

            # p.locked_out = True
            # p.save()

            create_message("buzz_init", p, None, room)

            self.send_json(
                {
                    "response_type": "buzz_grant",
                    "guess": guess,
                }
            )
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    "type": "update_room",
                    "data": get_room_response_json(room),
                },
            )

    def buzz_answer(self, room: Room, player: Player, content):

        self.log_tool_use(room, player, "", dict(), "buzz", "start")

        # Reject when not in contest
        if room.state != Room.GameState.CONTEST:
            return

        # Abort if no buzz player or current question
        if room.buzz_player == None or room.current_question == None:
            return

        if player.player_id == room.buzz_player.player_id:

            cleaned_content = clean_content(content)
            answered_correctly: bool = judge_answer(
                cleaned_content, room.current_question
            )
            # answered_correctly: bool = judge_answer_kuiperbowl(cleaned_content, room.current_question.answer)
            #words_to_show: int = room.compute_words_to_show()

            room.last_guess = cleaned_content
            room.save()

            if answered_correctly:
                player.score += 10
                player.correct += 1
                player.save()

                # Quick end question
                room.end_time = room.start_time
                room.buzz_player = None

                room.save()
                create_message(
                    "buzz_correct",
                    player,
                    cleaned_content,
                    room,
                )

                self.log_tool_use(room, player, {'guess': cleaned_content, 'true': room.current_question.answer_accept}, {'prediction': answered_correctly}, "buzz", "success")

                room.state = Room.GameState.IDLE
                self.update_status(room, "buzz_correct", player, cleaned_content)

                room.save()
                self.log_leaderboard(room, player)
                self.show_and_disable_tools(room=room, player=player)
                self.disable_plan()
            else:

                # keep playing if it's wrong
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

                # self.send_json({
                #     "response_type": "lock_out",
                #     "locked_out": True,
                # })

                buzz_duration = timezone.now().timestamp() - room.buzz_start_time
                room.start_time += buzz_duration
                room.end_time += buzz_duration
                room.save()

                self.log_tool_use(room, player, {'guess': cleaned_content, 'true': room.current_question.answer_accept}, {'prediction': answered_correctly}, "buzz", "failure")
                self.update_status(room, "buzz_incorrect", player, cleaned_content)

            # current_question: Question = room.current_question
            # try:
            #     feedback = QuestionFeedback.objects.get(
            #         question=current_question, player=player
            #     )
            # except QuestionFeedback.DoesNotExist:
            #     feedback = QuestionFeedback.objects.create(
            #         question=current_question,
            #         player=player,
            #         guessed_answer=cleaned_content,
            #         submitted_clue_list=current_question.clue_list,
            #         submitted_clue_order=list(range(current_question.length)),
            #         submitted_factual_mask_list=[0.5] * current_question.length,
            #         answered_correctly=answered_correctly,
            #         buzzed=True,
            #         buzz_position_word=words_to_show,
            #         buzz_position_norm=words_to_show
            #         / len(current_question.content.split()),
            #         buzz_datetime=timezone.now(),
            #     )
            #     feedback.save()
            # except ValidationError as e:
            #     pass

            #self.get_shown_question(room=room)

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    "type": "update_room",
                    "data": get_room_response_json(room),
                },
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
                    "type": "update_room",
                    "data": get_room_response_json(room),
                },
            )

            self.log_tool_use(room, player, "", dict(), "buzz", "forfeit")
            self.update_status(room, "buzz_abstain", player)

    def submit_initial_feedback(self, room: Room, player: Player, content):
        if room.state == Room.GameState.IDLE:
            try:
                current_question: Question = room.current_question
                feedback = QuestionFeedback.objects.get(
                    question=current_question, player=player
                )
                if feedback.initial_submission_datetime is None:
                    feedback.guessed_generation_method = content[
                        "guessed_generatation_method"
                    ]
                    feedback.interestingness_rating = content["interestingness_rating"]
                    feedback.initial_submission_datetime = timezone.now()
                    feedback.is_submitted = True

                    feedback.solicit_additional_feedback = (
                        feedback.guessed_generation_method
                        == Question.GenerationMethod.AI
                        or not current_question.is_human_written
                    )

                    feedback.guessed_gen_method_correctly = (
                        current_question.is_human_written
                        and feedback.guessed_generation_method
                        == Question.GenerationMethod.HUMAN
                    ) or (
                        not current_question.is_human_written
                        and feedback.guessed_generation_method
                        == Question.GenerationMethod.AI
                    )

                    feedback.save()
            except ValidationError as e:
                print(
                    f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}"
                )
            except KeyError as e:
                print(
                    f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}"
                )
                print(f"KeyError: {e}")

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    "type": "update_room",
                    "data": {
                        "response_type": "get_question_feedback",
                        "question_feedback": get_question_feedback_response_json(
                            feedback
                        ),
                    },
                },
            )

    def submit_additional_feedback(self, room: Room, player: Player, content):
        if room.state == Room.GameState.IDLE:
            try:
                current_question: Question = room.current_question
                feedback = QuestionFeedback.objects.get(
                    question=current_question, player=player
                )
                if feedback.additional_submission_datetime is None:
                    feedback.submitted_clue_order = content["submitted_clue_order"]
                    feedback.submitted_factual_mask_list = content[
                        "submitted_factual_mask_list"
                    ]

                    # When counting inversions, we should ignore clues marked non-factual, since untrue things probably
                    # shouldn't have a "difficulty"
                    clue_order_for_factual_clues = list(
                        filter(
                            lambda i: feedback.submitted_factual_mask_list[i] >= 0.5,
                            feedback.submitted_clue_order,
                        )
                    )
                    feedback.inversions = count_inversions(clue_order_for_factual_clues)
                    feedback.submitted_clue_list = [
                        current_question.clue_list[i]
                        for i in feedback.submitted_clue_order
                    ]

                    feedback.improved_question = content["improved_question"]
                    feedback.feedback_text = content["feedback_text"]
                    feedback.additional_submission_datetime = timezone.now()
                    feedback.is_submitted = True

                    feedback.save()
            except ValidationError as e:
                print(
                    f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}"
                )
            except KeyError as e:
                print(
                    f"Error: failed to save initial feedback for {player.user.user_id} for question {current_question.question_id}"
                )
                print(f"KeyError: {e}")

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    "type": "update_room",
                    "data": {
                        "response_type": "get_question_feedback",
                        "question_feedback": get_question_feedback_response_json(
                            feedback
                        ),
                    },
                },
            )

    def get_answer(self, room, player):
        """Get answer for room question"""

        self.update_time_state(room, player)

        if room.state == Room.GameState.IDLE:
            # Generate random question for now if empty
            if room.current_question == None:
                pass
                # questions = Question.objects.all()

                # # Abort if no questions
                # if len(questions) <= 0:
                #     return

                # q = random.choice(questions)
                # q.answer = ""
                # q.content = ""
                # room.current_question = q
                # room.save()

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

    def update_experiment_type(self, user: User):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': {
                    "response_type": "set_experiment_type",
                    "experiment_type": user.experiment_group,
                    "category_preference": user.category_preference,
                },
            }
        )

    def get_shown_question(self, room: Room):
        """Computes the correct amount of the question to show, depending on the state of the game.
        Note, this value is not persisted because, updating is too expensive."""
        # print('shown', room.state, room.current_question)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "get_shown_question",
                    "shown_question": room.get_shown_question(),
                    "is_tutorial": room.current_question.generation_method == Question.GenerationMethod.TUTORIAL,
                    "state": room.state,
                },
            },
        )

    def decide_instruction_to_show(self, room: Room, player: Player):
        """Decide which instruction the user should see"""

        if room.current_question.generation_method in {Question.GenerationMethod.ATTENTION_PAIRWISE, Question.GenerationMethod.ATTENTION_SWAP}:
            return "A"

        # if users can swap, give them a random plan, as they can switch to the other one
        if player.user.experiment_group == User.ExperimentGroup.SWAP:
            return "A" if random.uniform(0, 1) > 0.5 else "B"

        # otherwise, quantify which one has been seen less and show that one to balance out the labels
        instruction_obj = AnswerData.objects.filter(
            question_id=room.current_question.question_id, did_comparison=True, is_final=True, is_report=False, followed_plan=True
        )
        seen_instr_A, seen_instr_B = (
            instruction_obj.filter(final_instructions_letter="A").values("user_id").distinct(),
            instruction_obj.filter(final_instructions_letter="B").values("user_id").distinct(),
        )
        num_shown_A, num_shown_B = seen_instr_A.count(), seen_instr_B.count()
        print(num_shown_A, num_shown_B)
        if num_shown_A == num_shown_B:
            return "A" if random.uniform(0, 1) > 0.5 else "B"
        return "A" if num_shown_A < num_shown_B else "B"

    def decrease_steps(self, room: Room, player: Player, subanswers: List[str]):
        """Decrease the number of steps by 1"""

        self.log_tool_use(
            room, player, {}, {'curr_subanswers': subanswers}, "decrease_steps", "start"
        )

        if room.curr_instructions_letter == "A":
            room.steps_seen_a -= 1
        elif room.curr_instructions_letter == "B":
            room.steps_seen_b -= 1
        room.save()

        self.log_tool_use(
            room, player, {}, {'curr_subanswers': subanswers[:-1]}, "decrease_steps", "success"
        )

    def send_subanswers(
        self,
        room: Room,
        player: Player,
        subanswers: List[str],
        is_correct: bool,
        is_final: bool,
        followed_plan: bool,
        notes: str,
    ):
        """Log the subanswers"""
        if room.curr_instructions_letter == None:
            return

        if room.curr_instructions_letter == "A":
            room.curr_subanswers_a = subanswers
        elif room.curr_instructions_letter == "B":
            room.curr_subanswers_b = subanswers

        room.save()
        room.refresh_from_db()

        self.log_answers(
            room=room, 
            player=player,
            is_correct=is_correct, 
            is_final=is_final, 
            followed_plan=followed_plan, 
            true_answer=room.current_question.answer_accept, 
            guessed_answer=room.last_guess,
            notes=notes
        )

    def swap_plan(self, room: Room, player: Player, subanswers: List[str]):
        """Swap the plan for the user"""

        if room.curr_instructions_letter == None:
            return

        old_letter = room.curr_instructions_letter
        self.log_tool_use(room, player, old_letter, {'num_steps_seen': room.steps_seen_a if old_letter == "A" else room.steps_seen_b, 'curr_subanswers': subanswers}, "swap_instructions", "start")

        if old_letter == "A":
            swapped_letter = "B"
            new_steps = room.steps_seen_b
            if new_steps == 0:
                new_steps = 1
                room.steps_seen_b = new_steps
            room.curr_subanswers_a = subanswers
            new_subanswers = room.curr_subanswers_b
        else:
            swapped_letter = "A"
            new_steps = room.steps_seen_a
            if new_steps == 0:
                new_steps = 1
                room.steps_seen_a = new_steps
            room.curr_subanswers_b = subanswers
            new_subanswers = room.curr_subanswers_a

        room.curr_instructions_letter = swapped_letter
        room.save()
        room.refresh_from_db()

        self.updated_swapped_instructions(
            room=room, player=player, num_steps=new_steps, subanswers=new_subanswers
        )

        self.log_tool_use(
            room, player, old_letter, {'num_steps_seen': room.steps_seen_a if swapped_letter == "A" else room.steps_seen_b, 'curr_subanswers': [''] if new_subanswers == None else new_subanswers}, "swap_instructions", "success"
        )

    def load_instructions(self, room: Room, player: Player):
        """Load instructions to show to the user"""
        instruction_label = self.decide_instruction_to_show(room=room, player=player)
        room.curr_instructions_letter = instruction_label
        room.save()
        room.refresh_from_db()

    def show_next_step(self, room: Room, player: Player, subanswers):
        """Show the next step to the user"""

        self.log_tool_use(
            room, player, {}, {'curr_subanswers': subanswers}, "next_step", "start"
        )

        if room.curr_instructions_letter == None:
            self.load_instructions(room=room, player=player)

        curr_steps = (
            room.steps_seen_a
            if room.curr_instructions_letter == "A"
            else room.steps_seen_b
        )

        curr_instr = (
            room.current_question.instructions_a
            if room.curr_instructions_letter == "A"
            else room.current_question.instructions_b
        )

        if curr_steps == len(curr_instr["steps"]):
            return

        if room.curr_instructions_letter == "A":
            room.steps_seen_a += 1
        elif room.curr_instructions_letter == "B":
            room.steps_seen_b += 1

        room.save()
        curr_steps += 1
        self.get_init_model_instructions(
            room=room, player=player, num_steps=curr_steps, should_clear=False
        )

        self.log_tool_use(
            room, player, {}, {'curr_subanswers': subanswers + ['']}, "next_step", "success"
        )

    def updated_swapped_instructions(
        self, room: Room, player: Player, num_steps: int, subanswers
    ) -> None:
        """After the players are ready for the next question, show them the right instructions"""

        instructions_label = room.curr_instructions_letter
        instructions = (
            room.current_question.instructions_a
            if instructions_label == "A"
            else room.current_question.instructions_b
        )

        # Send instructions only to the player's WebSocket
        async_to_sync(self.channel_layer.send)(
            player.channel_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "update_swapped_instructions",
                    "instructions": {"steps": instructions["steps"][:num_steps]},
                    "subanswers": subanswers,
                    "is_last_step": num_steps == len(instructions["steps"]),
                },
            },
        )

    def clear_instructions(self, room: Room, player: Player):
        async_to_sync(self.channel_layer.send)(
            player.channel_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "clear_instructions",
                },
            },
        )

    def get_init_model_instructions(
        self, room: Room, player: Player, num_steps: int, should_clear: bool
    ) -> None:
        """After the players are ready for the next question, show them the right instructions"""

        instructions = (
            room.current_question.instructions_a
            if room.curr_instructions_letter == "A"
            else room.current_question.instructions_b
        )

        curr_steps = instructions["steps"] if room.current_question.generation_method != Question.GenerationMethod.ATTENTION_PAIRWISE else instructions["steps_leaked"]

        print(room.current_question.generation_method)

        # Send instructions only to the player's WebSocket
        async_to_sync(self.channel_layer.send)(
            player.channel_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "update_instructions",
                    "instructions": {
                        "steps": (
                            curr_steps
                            if num_steps == -1
                            else curr_steps[:num_steps]
                        )
                    },
                    "step_num": num_steps,
                    "is_last_step": num_steps == len(curr_steps),
                    "should_clear": should_clear,
                },
            },
        )

    def update_tools_and_doc_for_question_and_player(self, room: Room, player: Player):
        """Update the visible tools and document based on the current question for just one player"""
        question = room.current_question

        self.update_tools(
            self.channel_layer.group_send,
            self.room_group_name,
            (question is None and room.category in {Question.Category.MATH, Question.Category.EVERYTHING}) or (question is not None and question.category == Question.Category.MATH),
            (question is None and room.category in {Question.Category.MULTIHOP}) or (question is not None and question.category == Question.Category.MULTIHOP),
            (question is None and room.category in {Question.Category.MULTIHOP}) or (question is not None and question.category == Question.Category.MULTIHOP),
        )
        curr_doc = ""
        self.update_doc(
            self.channel_layer.group_send,
            self.room_group_name,
            (question is None and room.category in {Question.Category.MULTIHOP}) or (question is not None and question.category == Question.Category.MULTIHOP),
            curr_doc,
        )

    def disable_plan(self):
        """Helper function to disable the plan"""
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "disable_plan",
                },
            },
        )

    def show_and_disable_tools(self, room: Room, player: Player):
        """Update the visible tools and document based on the current question"""
        self.update_tools_and_doc_for_question_and_player(room=room, player=player)
        self.disable_tool_btns(
            room=room,
            player=player,
            should_disable=True,
            should_clear_document=((room.current_question is None and room.category in {Question.Category.MULTIHOP}) or (room.current_question is not None and room.current_question.category == Question.Category.MULTIHOP)),
        )

    def update_status(self, room: Room, status: str, player: Player, answer=""):
        """Helper function to update the status text"""
        if player.channel_name == "":
            return
        async_to_sync(self.channel_layer.send)(
            player.channel_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "update_status",
                    "status": status,
                    "player": player.user.name,
                    "answer": answer,
                    "allow_swaps": not room.show_comparisons_before,
                },
            },
        )

    def disable_tool_btns(
        self,
        room: Room,
        player: Player,
        should_disable: bool,
        should_clear_document: bool,
    ):
        """Helper function to enable/disable the tool buttons"""
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "disable_tools",
                    "should_disable": should_disable,
                    "should_clear_document": should_clear_document,
                },
            },
        )

    def update_doc(self, channel_layer_send, player_channel, use_doc, doc_content):
        """Helper function to update document info"""
        async_to_sync(channel_layer_send)(
            player_channel,
            {
                "type": "update_room",
                "data": {
                    "response_type": "update_doc",
                    "use_doc": use_doc,
                    "doc_content": doc_content,
                },
            },
        )

    def update_tools(
        self, channel_layer_send, player_channel, use_calc, use_doc, use_web
    ):
        """Helper function to update tool info"""
        async_to_sync(channel_layer_send)(
            player_channel,  # Each player has their unique channel_name
            {
                "type": "update_room",
                "data": {
                    "response_type": "update_tools",
                    "use_calculator": use_calc,
                    "use_doc": use_doc,
                    "use_web": use_web,
                },
            },
        )

    def get_init_question_feedback(self, room: Room, player: Player) -> None:
        """After a question is completed (i.e. the room becomes idle),
        send a message containing the feedback regarding the question"""

        # Cannot request during playing or contesting
        if room.state is Room.GameState.IDLE:
            return

        current_question: Question = room.current_question

        try:
            feedback = QuestionFeedback.objects.get(
                question=current_question, player=player
            )
        except QuestionFeedback.DoesNotExist:
            feedback = createFeedbackNoBuzz(room=room, player=player)
            feedback.save()
        except ValidationError as e:
            pass

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "get_question_feedback",
                    "question_feedback": get_question_feedback_response_json(feedback),
                },
            },
        )

    def set_category(self, room, p, content):
        """Set room category"""
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
                    "type": "update_room",
                    "data": get_room_response_json(room),
                },
            )
        except ValidationError as e:
            pass

    def set_difficulty(self, room, p, content):
        """Set room difficulty"""
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
                    "type": "update_room",
                    "data": get_room_response_json(room),
                },
            )
        except ValidationError as e:
            pass

    def set_speed(self, room, p, content):
        """Set room speed"""
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
                    "type": "update_room",
                    "data": get_room_response_json(room),
                },
            )
        except ValidationError as e:
            pass

    def reset_score(self, room, p):
        """Reset player score"""

        p.score = 0
        p.save()

        create_message("reset_score", p, None, room)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": get_room_response_json(room),
            },
        )

    def chat(self, room, p, content):
        """Send chat message"""

        m = clean_content(content)

        create_message("chat", p, m, room)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "update_room",
                "data": get_room_response_json(room),
            },
        )

    def kick(self):
        """Kick banned player"""
        self.send_json(
            {
                "response_type": "kick",
            }
        )
        async_to_sync(self.channel_layer.group_discard)(
            self.room_name, self.channel_name
        )

    def too_many_players(self):
        """Too many players in a room. Cannot join room."""
        self.send_json(
            {
                "response_type": "too_many_players",
            }
        )
        async_to_sync(self.channel_layer.group_discard)(
            self.room_name, self.channel_name
        )

    def report_issue(self, room: Room, p: Player, report_data):
        ReportIssue.objects.create(
            user=p.user,
            question_id=room.current_question.question_id,
            is_bad_question=report_data['is_bad_question'],
            is_bad_instruction=report_data['is_bad_instruction'],
            is_bad_answer_verifier=report_data['is_bad_answer_verifier'],
            is_frustrated=report_data['is_frustrated'],
            feedback=report_data['feedback']
        )
        self.handle_no_buzz(room, p, True)

    def report_message(self, room: Room, p: Player, message_id):
        """Handle reporting messages"""
        m = room.messages.filter(message_id=message_id).first()
        if m == None:
            return

        # Only report chat or buzz messages
        if m.tag == "chat" or m.tag == "buzz_correct" or m.tag == "buzz_wrong":
            m.player.reported_by.add(p)
            m.save()

            # Ban if reported by 60% of players
            num_players_in_room = len(room.get_valid_players())
            ratio = len(m.player.reported_by.all()) / num_players_in_room
            if ratio > 0.6 and num_players_in_room > 1:
                m.player.banned = True
                m.player.save()

    def log_answers(
        self, room: Room, player: Player, is_correct: bool, is_final: bool, followed_plan: bool, guessed_answer: str, true_answer: str, notes: str,
    ):
        """Log the user's progress on completing the instructions"""

        # first, check if the question has already been reported
        q = ReportIssue.objects.filter(user=player.user, question_id=room.current_question.question_id)
        is_report = len(q) > 0

        # if not found, log normally
        AnswerData.objects.create(
            user=player.user,
            question_id=room.current_question.question_id,
            category=room.current_question.category,
            final_instructions_letter=room.curr_instructions_letter,
            instructions_a=room.current_question.instructions_a,
            instructions_b=room.current_question.instructions_b,
            subanswers_a=(
                dict() if room.curr_subanswers_a == None else room.curr_subanswers_a
            ),
            subanswers_b=(
                dict() if room.curr_subanswers_b == None else room.curr_subanswers_b
            ),
            steps_seen_a=room.steps_seen_a,
            steps_seen_b=room.steps_seen_b,
            did_comparison=room.show_comparisons_before,
            is_correct=is_correct,
            is_final=is_final,
            is_report=is_report,
            followed_plan=followed_plan,
            true_answer=true_answer,
            guessed_answer=guessed_answer,
            notes=notes,
        )

    def log_leaderboard(self, room: Room, p: Player):
        """Log the stats on this question for the leaderboard"""

        # find the last time the user looked at the question
        last_question_call = ToolLog.objects.filter(
            user_id=p.user.user_id,
            question_id=room.current_question.question_id,
            tool_name="question"
        ).order_by("-queried_at").first()

        # get all subsequent tool calls
        if last_question_call:
            tool_calls = ToolLog.objects.filter(
                user_id=p.user.user_id,
                question_id=room.current_question.question_id,
                queried_at__gte=last_question_call.queried_at
            ).order_by("queried_at")
        else:
            print("ERROR: Question was never logged")
            return

        all_buzzes = tool_calls.filter(tool_name="buzz")
        num_buzzes = all_buzzes.count() // 2
        num_correct_buzzes = all_buzzes.filter(tool_execution_status="success").count()

        if num_buzzes == 0:
            correctness = 0.0
        else:
            correctness = (1.0 * num_correct_buzzes) / num_buzzes

        print("Tools:", [(t.tool_name, t.tool_execution_status, t.queried_at) for t in tool_calls])

        tool_calls = list(tool_calls)
        total_time_taken = (
            tool_calls[-1].queried_at - tool_calls[2].queried_at
        ).total_seconds()
        if tool_calls[-1].tool_name == "no_buzz":
            tool_calls_noninstruct = tool_calls[3:-1]
        else:
            tool_calls_noninstruct = tool_calls[3:]

        tool_runtime = 0
        for idx in range(len(tool_calls_noninstruct) // 2):
            tool_start, tool_end = (
                tool_calls_noninstruct[2 * idx],
                tool_calls_noninstruct[2 * idx + 1],
            )
            tool_runtime += (
                tool_end.queried_at - tool_start.queried_at
            ).total_seconds()

        LeaderboardLog.objects.create(
            user=p.user,
            question_id=room.current_question.question_id,
            correctness_score=correctness,
            total_time_taken=total_time_taken,
            tool_runtime=tool_runtime,
            seconds_taken=(total_time_taken - tool_runtime),
            did_comparison=room.show_comparisons_before,
        )

    def log_tool_use(
        self,
        room: Room,
        p: Player,
        tool_query: str,
        tool_result: dict,
        tool_name: str,
        status: str,
    ):
        """Log the tool that was used"""
        ToolLog.objects.create(
            user_id=p.user.user_id,
            question_id=room.current_question.question_id,
            instruction_type=room.curr_instructions_letter,
            tool_name=tool_name,
            tool_query=tool_query,
            tool_result=tool_result,
            tool_execution_status=status,
        )

    def send_web_search_error(self, room: Room, p: Player, query: str, error=""):
        """Handle errors during web search"""

        room.curr_query = None
        room.save()

        self.send(text_data=json.dumps({
            'response_type': 'web_search_result',
            'result': f"<p>No results found: {error}\nTry another search query!</p>"
        }))
        self.send(
            text_data=json.dumps(
                {
                    "response_type": "web_search_result",
                    "result": f"<p>No results found: {error}\nTry another search query!</p>",
                }
            )
        )

        # log tool use
        self.log_tool_use(room, p, query, {"error": error}, "web_search", "failure")

    def retrieve_from_document_cache(self, key: str):
        doc_obj = Document.objects.filter(doc_id=key)
        if doc_obj.count() == 0:
            return None
        return doc_obj.first().document_text

    def add_to_document_cache(self, key: str, value: str):
        Document.objects.create(doc_id=key, document_text=value)

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
        self.log_tool_use(room, p, query, dict(), "web_search", "start")

        cached_query_res = self.retrieve_from_document_cache(
            "wiki_title_query:" + query
        )
        if cached_query_res != None:
            return [cached_query_res], "from_cache"

        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            search_engine_id = os.getenv("GOOGLE_CSE_ID")
            google_search_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": api_key,
                "cx": search_engine_id,
                "q": query,
                "num": 10,
            }
            response = requests.get(google_search_url, params=params)
            response_data = response.json()
            search_results = response_data.get("items", [])
            if not search_results:
                return ["no_search_results"], "error"
        except Exception as e:
            return [str(e)], "error"

        return [
            r["title"].replace(" - Wikipedia", "").strip() for r in search_results
        ], "new_search"

    def extract_elements_from_html(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        elements = soup.find_all(id=re.compile(r"^element-"))
        sentences = []
        for elem in elements:
            sentences.append(elem.text.strip())
        return sentences

    def send_web_search_success(
        self,
        room: Room,
        p: Player,
        query: str,
        title: str,
        final_html: str,
        cache_title: bool,
        cache_html: bool,
    ):
        """Successful web search"""

        if cache_title:
            self.add_to_document_cache("wiki_title_query:" + query, title)
        if cache_html:
            self.add_to_document_cache("wiki_page_query:" + title, final_html)

        self.log_tool_use(room, p, query, title, "web_search", "success")
        self.send(
            text_data=json.dumps(
                {"response_type": "web_search_result", "result": final_html}
            )
        )
        self.update_tools(
            self.channel_layer.send,
            p.channel_name,
            room.current_question.uses_calculator,
            True,
            True,
        )

        # auto-search for the relevant paragraph
        self.select_content(room, p, query, final_html)

    def web_search(self, room: Room, p: Player, query):

        wiki_pages, status = self.get_wiki_pages(room, p, query)
        if status == "error":
            print(wiki_pages, status)
            self.send_web_search_error(room, p, query, wiki_pages[0])
            return

        session = self.scope["session"]
        wikimedia_token = session.get("oauth_token")
        oauth_session = OAuth2Session(
            os.getenv("WIKIMEDIA_CLIENT_ID"), token=wikimedia_token
        )

        for page_title in wiki_pages:
            page_title_clean = self.clean_query(page_title)

            cached_page_res = self.retrieve_from_document_cache(
                "wiki_page_query:" + page_title_clean
            )

            if cached_page_res != None:
                room.curr_query = page_title_clean
                room.save()

                print("page found in cache!")
                self.send_web_search_success(
                    room=room,
                    p=p,
                    query=self.clean_query(query),
                    title=page_title_clean,
                    final_html=cached_page_res,
                    cache_title=(status == "new_search"),
                    cache_html=False,
                )
                return

            params = {
                "action": "parse",
                "page": page_title,
                "format": "json",
                "prop": "text|images",
                "redirects": 1,
            }

            try:
                api_url = "https://en.wikipedia.org/w/api.php"
                response = oauth_session.get(api_url, params=params)
            except TokenExpiredError:
                self.send(
                    text_data=json.dumps(
                        {
                            "response_type": "reauthenticate",
                        }
                    )
                )
                self.close()
                return
            except Exception as e:
                continue

            if response.status_code == 200:

                room.curr_query = page_title_clean
                room.save()

                data = response.json()
                html_content = data["parse"]["text"]["*"]
                title = data["parse"]["title"]
                soup = BeautifulSoup(html_content, "html.parser")

                # TODO: fix the web scraping

                element_counter = 0
                for p_tag in soup.find_all("p"):
                    text = p_tag.get_text()
                    sentences = nltk.sent_tokenize(text)
                    curr_html = ""
                    for sent in sentences:
                        if sent:
                            curr_html += (
                                f'<span id="element-{element_counter}">{sent}</span> '
                            )
                            element_counter += 1
                    p_tag.clear()
                    p_tag.append(BeautifulSoup(curr_html, "html.parser"))

                # for li_tag in soup.find_all('li'):
                #     if not (li_tag.a and len(li_tag.contents) == 1):
                #         text = li_tag.get_text()
                #         if text:
                #             content_list.append(text)
                #             li_tag['id'] = f"element-{element_counter}"
                #             element_counter += 1

                fixed_html_content = str(soup)
                openbracket, closebracket = "{", "}"
                wikipedia_css = """
                <link rel="stylesheet" href="https://en.wikipedia.org/w/load.php?debug=false&lang=en&modules=mediawiki.legacy.shared|mediawiki.skinning.content|mediawiki.skinning.interface&only=styles&skin=vector">
                <link rel="stylesheet" href="https://en.wikipedia.org/w/load.php?debug=false&lang=en&modules=site.styles&only=styles&skin=vector">
                """
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
                copy_script = ""
                final_html = f"""
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
                """
                print("new page")
                self.send_web_search_success(
                    room=room,
                    p=p,
                    query=self.clean_query(query),
                    title=page_title_clean,
                    final_html=final_html,
                    cache_title=(status == "new_search"),
                    cache_html=True,
                )

                return
            else:
                continue

        self.send_web_search_error(room, p, query, "no_page_content")

    def log_comparison(self, room: Room, p: Player, chosen: str):
        """Log pairwise comparison of instructions"""
        chosen_adjusted = chosen
        if chosen_adjusted not in {"Tie", "None"} and room.instruction_map["swapped"]:
            chosen_adjusted = "A" if chosen == "B" else "B"
        ComparisonFeedback.objects.create(
            question=room.current_question,
            user=p.user,
            chosen=chosen,
            chosen_adjusted=chosen_adjusted,
            chosen_instruction=(
                chosen if chosen in {"Tie", "None"} else room.instruction_map[chosen]
            ),
            shown_first=room.show_comparisons_before,
        )

        room.state = Room.GameState.INSTRUCTION_READING
        room.save()
        self.toggle_comparison_visibility(room=room, show_comparison=False)

        #self.clear_instructions(room=room, player=p)
        self.show_and_disable_tools(room=room, player=p)
        #self.get_shown_question(room=room)
        self.next(room, p)

    def clean_query(self, query):
        """Clean the query for cached lookup"""
        cleaned_query = re.sub(r"[^a-zA-Z0-9\s\-]", "", query)
        cleaned_query = re.sub(r"\s+", "-", cleaned_query.strip())
        return cleaned_query.lower()

    def select_content_wrapper(self, room: Room, p: Player, query: str):
        """ Wrapper for long-context content selection """

        # if current document doesnt exist
        if (room.current_question.category == Question.Category.LONGCONTEXT and not room.current_question.document_context) or (not room.curr_query):
            return
        
        print("current query:", room.curr_query)
        
        search_query = 'long_context:' + room.current_question.document_context if (room.current_question.category == Question.Category.LONGCONTEXT) else 'wiki_page_query:' + room.curr_query
        html = self.retrieve_from_document_cache(search_query)
        self.select_content(room, p, query, html)

    def select_content(self, room: Room, p: Player, query: str, html: str):
        """Executes the content selection tool"""

        self.log_tool_use(room, p, query, dict(), "content_selection", "start")
        docs = self.extract_elements_from_html(html)

        cohere_client = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

        try:
            retr_results = cohere_client.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=docs,
                top_n=1,
                return_documents=True,
            )
        except Exception as e:
            self.send(
                text_data=json.dumps(
                    {
                        "response_type": "content_selection_result",
                        "result": [],
                    }
                )
            )
            self.log_tool_use(
                room, p, query, {"error": str(e)}, "content_selection", "failure"
            )
            return

        retr_docs = [d.document.text for d in retr_results.results]
        retr_docs = [re.sub(r"\[.*?\]", " ", doc) for doc in retr_docs]
        retr_docs = [re.sub(r"\s+", " ", doc).strip() for doc in retr_docs]
        doc_idxs = [int(d.index) for d in retr_results.results]

        self.log_tool_use(
            room,
            p,
            query,
            {"retrieved_docs": retr_docs, "doc_idxs": doc_idxs},
            "content_selection",
            "success",
        )

        # Send the retrieved content back to the frontend
        self.send(
            text_data=json.dumps(
                {
                    "response_type": "content_selection_result",
                    "result": doc_idxs,
                    "num_docs": len(docs),
                }
            )
        )

    def calculate(self, room: Room, p: Player, equation):
        """Executes the calculator tool using SymPy with implicit multiplication handling"""
        self.log_tool_use(room, p, equation, dict(), "calculator", "start")

        # Define allowed symbols and functions
        allowed_symbols = {
            "sqrt": sqrt,
            "abs": Abs,
            "round": round,
            "pi": pi,  # Include 'pi' if you want to allow it
        }

        # Set up the transformations to include implicit multiplication
        transformations = standard_transformations + (
            implicit_multiplication_application,
        )

        try:
            # Parse the expression using parse_expr with allowed symbols and transformations
            expr = parse_expr(
                equation,
                local_dict=allowed_symbols,
                transformations=transformations,
                evaluate=True,
            )

            # Evaluate the expression numerically
            result = expr.evalf()

            # Apply rounding to 4 decimal places
            result = round(float(result), 4)

            # Log tool use
            self.log_tool_use(
                room, p, equation, {"calculation": result}, "calculator", "success"
            )

            self.send(
                text_data=json.dumps(
                    {"response_type": "calculation_result", "result": result}
                )
            )

        except (SympifyError, TypeError, ValueError) as e:
            # Log tool use with error
            self.log_tool_use(
                room, p, equation, {"error": str(e)}, "calculator", "failure"
            )

            self.send(
                text_data=json.dumps(
                    {"response_type": "calculation_result", "result": "ERROR"}
                )
            )

    # === Helper methods ===

    def update_time_state(self, room: Room, player: Player):
        pass

    def log_report_answer(self):
        pass

    def handle_no_buzz(self, room: Room, player: Player, is_report: bool):

        if room.state == Room.GameState.PLAYING:

            if is_report:
                self.log_tool_use(room, player, "", dict(), "report", "start")
            else:
                self.log_tool_use(room, player, "", dict(), "no_buzz", "start")
                self.log_leaderboard(room, player)
            # self.log_answers(room, player, False)

            # curr_answer = ''
            # if not room.show_comparisons_before:
            #     room.state = Room.GameState.PAIRWISE_COMPARISON
            #     self.toggle_comparison_visibility(room, True)
            #     self.update_status(room, room.state + '_incorrect', player, curr_answer)
            # else:
            room.state = Room.GameState.IDLE
            curr_answer = room.current_question.answer_accept[0]
            self.update_status(room, room.state, player, curr_answer)
            room.save()

            self.get_init_model_instructions(
                room=room, player=player, num_steps=-1, should_clear=True
            )
            self.show_and_disable_tools(room=room, player=player)
            self.disable_plan()


def get_room_response_json(room):
    """Generates JSON for update response"""

    return {
        "response_type": "update",
        "game_state": room.state,
        "current_time": timezone.now().timestamp(),
        "start_time": room.start_time,
        "end_time": room.end_time,
        "buzz_start_time": room.buzz_start_time,
        "category": (
            room.current_question.category if room.current_question != None else ""
        ),
        "room_category": room.category,
        "messages": room.get_messages(),
        "difficulty": room.difficulty,
        "speed": room.speed,
        "players": room.get_players_by_score(),
        "instruction_map": room.instruction_map,
        "change_locked": room.change_locked,
    }


def get_instructions_response_json(instructions: json) -> Dict:
    return dict(instructions)


def get_question_feedback_response_json(feedback: QuestionFeedback) -> Dict:
    feedback_json = serialize("json", [feedback])
    feedback_dict = json.loads(feedback_json)[0]["fields"]
    return feedback_dict


def create_message(tag, p, content, room):
    """Adds a message to db"""
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
        is_submitted=True,
        initial_submission_datetime=timezone.now(),
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

        temp.extend(arr[i : mid + 1])
        temp.extend(arr[j : right + 1])
        arr[left : right + 1] = temp

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
