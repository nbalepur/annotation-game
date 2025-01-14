from typing import Dict, List
from asgiref.sync import async_to_sync, sync_to_async
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from django.core.serializers import serialize
from django.shortcuts import redirect

from .models import *
from .utils import clean_content, generate_name, generate_id
from .judge import judge_answer

import aiohttp
import json
import os
import traceback
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

class QuizbowlConsumer(AsyncJsonWebsocketConsumer):
    """Websocket consumer for quizbowl game"""

    async def connect(self):
        """Websocket connect"""
        self.room_name = self.scope["url_route"]["kwargs"]["label"]
        self.room_group_name = f"game-{self.room_name}"

        # Validate user session
        self.user_id = self.scope["session"].get("user_id")
        if not self.user_id:
            await self.close()
            return

        try:
            await self.channel_layer.group_add(
                self.room_group_name, self.channel_name
            )
        except Exception as e:
            await self.close()
            return

        await self.accept()

    async def disconnect(self, close_code):
        """Websocket disconnect"""
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name
        )

    async def receive(self, text_data):
        """Websocket receive"""

        data = json.loads(text_data)
        if "content" not in data or data["content"] is None:
            data["content"] = ""

        # ensure the session is still valid
        session_user_id = self.scope["session"].get("user_id")
        if not session_user_id or session_user_id != self.user_id:
            await self.close()
            return

        room = await Room.objects.aget(label=self.room_name)

        if data["request_type"] == "new_user":
            user = await self.new_user()
            data["user_id"] = user.user_id
            await self.join(room, data)

        if "user_id" not in data or "request_type" not in data:
            return

        user_exists = await User.objects.filter(user_id=data["user_id"]).aexists()
        if not user_exists:
            user = await self.new_user()
            data["user_id"] = user.user_id

        # Handle join
        if data["request_type"] == "join":
            await self.join(room, data)
            return

        # Get player
        p = await room.players.filter(user__user_id=data['user_id']).afirst()
        # Update connection if it's new
        if p and p.channel_name != self.channel_name:
            p.channel_name = self.channel_name
            await p.asave()

        if p:
            # Kick if banned user
            if p.banned:
                await self.kick()
                return

            # Handle requests for joined players
            if data["request_type"] == "ping":
                await self.ping(room, p)
            elif data["request_type"] == "leave":
                await self.leave(room, p)
            elif data["request_type"] == "set_user_data":
                await self.set_user_data(room, p, data["content"])
            elif data["request_type"] == "next":
                await self.next(room, p)
            elif data["request_type"] == "skip":
                await self.skip(room, p)
            elif data["request_type"] == "show_next_step":
                await self.show_next_step(room=room, player=p, subanswers=data["content"])
            elif data["request_type"] == "swap_plan":
                await self.swap_plan(room=room, player=p, subanswers=data["content"])
            elif data["request_type"] == "send_subanswers":
                await self.send_subanswers(
                    room=room,
                    player=p,
                    subanswers=data["content"]["subanswers"],
                    is_correct=data["content"]["is_correct"],
                    is_final=data["content"]["is_final"],
                    followed_plan=data["content"]["followed_plan"],
                    notes=data["content"]["notes"]
                )
            elif data["request_type"] == "buzz_init":
                await self.buzz_init(room, p, data["content"])
            elif data["request_type"] == "buzz_answer":
                await self.buzz_answer(room, p, data["content"])
            elif data["request_type"] == "no_buzz":
                await self.handle_no_buzz(room, p, False)
            elif data["request_type"] == "chat":
                await self.chat(room, p, data["content"])
            elif data["request_type"] == "report_issue":
                await self.report_issue(room, p, data["content"])
            elif data["request_type"] == "skip_plan":
                await self.skip_plan(room, p)
            elif data["request_type"] == "calculate":
                await self.calculate(room, p, data["content"])
            elif data["request_type"] == "web_search":
                await self.web_search(room, p, data["content"], False, True)
            elif data["request_type"] == "content_select":
                await self.select_content_wrapper(room, p, data["content"])
            elif data["request_type"] == "navigate_history":
                await self.navigate_history(room, p, data['content'])
            elif data["request_type"] == "log_comparison":
                await self.log_comparison(room, p, data["content"])
            elif data["request_type"] == "decrease_steps":
                await self.decrease_steps(room, p, data['content'])
            elif data["request_type"] == "change_category":
                await self.change_category(room, p, data['content'])
            elif data["request_type"] == "change_auto_scroll":
                await self.change_auto_scroll(room, p, data['content'])
            elif data["request_type"] == "navigate_hyperlink":
                await self.navigate_hyperlink(room, p, data['content'])
            else:
                pass

    async def update_room(self, event):
        """Room update handler"""
        await self.send_json(event["data"])

    async def ping(self, room, p):
        """Receive ping"""

        p.last_seen = timezone.now().timestamp()
        await p.asave()

        room_json = await get_room_response_json(room)
        await self.send_json(room_json)
        await self.send_json(
            {
                "response_type": "lock_out",
                "locked_out": p.locked_out,
            }
        )

    async def change_auto_scroll(self, room: Room, player: Player, auto_scroll: bool):
        user = await user_from_player(player)
        user.auto_scroll = auto_scroll
        await user.asave()

    async def change_category(self, room: Room, player: Player, category: str):
        category_map = {
            'Everything': Question.Category.EVERYTHING,
            'Math': Question.Category.MATH,
            'Trivia': Question.Category.MULTIHOP
        }
        
        user = await user_from_player(player)
        user.category_preference = category_map[category]
        await user.asave()

        old_category = room.category
        if old_category == category_map[category]:
            return
        room.category = category_map[category]
        await room.asave()

        if old_category in {Question.Category.MULTIHOP} and category_map[category] in {Question.Category.MULTIHOP, Question.Category.EVERYTHING}:
            return
        if old_category in {Question.Category.MATH} and category_map[category] in {Question.Category.MATH}:
            return

        await self.show_and_disable_tools(room=room, player=player, update_tools=True, disable_tools=True, disable_plan=True,
                                          category=Question.Category.MATH if category_map[category] == Question.Category.MATH else Question.Category.MULTIHOP)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": await get_room_response_json(room),
            },
        )

    async def join(self, room: Room, data):
        """Join room"""
        user = await User.objects.filter(user_id=data["user_id"]).afirst()
        if user is None:
            print("No user found!")
            return
        if user.experiment_group is None:
            print("No experiment group found!")
            return
        
        # Pass the experiment group settings to the front-end
        await self.update_experiment_type(user)
        
        room.steps_seen_a = 1
        room.steps_seen_b = 1
        room.curr_instructions_letter = None
        room.curr_subanswers_a = None
        room.curr_subanswers_b = None

        room.category = user.category_preference

        # Create player if doesn't exist
        p = await user.players.filter(room=room).afirst()

        # Get the players in the room that have last been seen within 10 seconds ago, excluding the user trying to join
        curr_players_count = await room.players.filter(
                Q(last_seen__gte=timezone.now().timestamp() - 10)
                & ~Q(user__user_id=data["user_id"])
            ).acount()

        if p is None and curr_players_count < room.max_players:
            p = await Player.objects.acreate(room=room, user=user)

        if curr_players_count >= room.max_players:
            await self.too_many_players()
            print("too many!")
        else:
            await create_message("join", p, None, room)

            room.state = Room.GameState.IDLE
            room_json = await get_room_response_json(room)
            await self.send_json(room_json)
            await room.asave()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "update_room",
                    "data": await get_room_response_json(room),
                },
            )

            # await self.update_status(room, room.state, p)
            # await self.show_and_disable_tools(room=room, player=p, update_tools=True)

            # await self.update_ui(room=room, player=p,
            #                          disable_inputs={'update_tools': True, 'disable_plan': False},
            #                          )

            p.last_room = self.room_name


    async def leave(self, room, p):
        """Leave room"""
        await create_message("leave", p, None, room)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": await get_room_response_json(room),
            },
        )

    # @sync_to_async
    # def decide_wiki_token_num(self, user: User):
    #     if user is not None:
    #         return user.wiki_token_num
    #     return random.choice([1, 2, 3])

    # backup to make sure that the user has an experiment group
    async def new_user(self):
        """Create new user and player in room"""
        user = await User.objects.filter(user_id=self.user_id).afirst()
        expt_group, is_new = await sync_to_async(get_or_create_expt_group)(user)
        if (is_new):
            user.experiment_group = expt_group
            await user.asave()
        await self.send_json(
            {
                "response_type": "new_user",
                "user_id": user.user_id,
                "user_name": user.name,
                "user_email": user.email,
            }
        )

        return user
    
    async def check_duplicate_user_data(self, adj_username, adj_email):
        """Check if there's duplicate information in the user data"""
        await self.channel_layer.group_send(
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

    async def set_user_data(self, room: Room, p: Player, content):
        """Update player name"""
        user = await user_from_player(p)

        # get the current owner of the user names + emails
        old_user_name = clean_content(content["user_name"])
        old_email = clean_content(content["user_email"])

        curr_username_user = User.objects.filter(name=old_user_name)
        curr_email_user = User.objects.filter(email=old_email)

        # check if these are valid to use: if no one exists, or if it's the current user
        username_is_valid = (
            not await curr_username_user.aexists() or 
            (await curr_username_user.afirst()).user_id == user.user_id
        )
        email_is_valid = (
            not await curr_email_user.aexists() or 
            (await curr_email_user.afirst()).user_id == user.user_id
        )

        # set the new values accordingly
        new_user_name = old_user_name if username_is_valid else ''
        new_email = old_email if email_is_valid else ''

        await self.check_duplicate_user_data(new_user_name, new_email)

        if username_is_valid or email_is_valid:

            user.name = new_user_name
            user.email = new_email

            try:
                await sync_to_async(user.full_clean)()
                await user.asave()

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "update_room",
                        "data": await get_room_response_json(room),
                    },
                )
            except ValidationError as e:
                return

    async def handle_not_enough_players(self, room: Room, send_alert: bool):
        """Logic to run when there's not enough players"""

        if send_alert:
            await self.send_json(
                {
                    "response_type": "not_enough_players",
                }
            )

    async def transition_to_instruction(self, room: Room, player: Player):
        """Logic for the transition state to instruction reading"""

        room.state = Room.GameState.INSTRUCTION_READING
        room.start_time = timezone.now().timestamp()
        room.end_time = (
            room.start_time + INSTRUCTION_READING_TIME
        )
        await room.asave()


        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": await get_room_response_json(room),
            },
        )

        user = await user_from_player(player)
        await self.update_ui(room=room, player=player,
                           show_question_inputs={'user': user},
                           status_inputs={'status': room.state},
                           instr_inputs={'should_clear': True, 'num_steps': -1},
                           disable_inputs={'update_tools': True, 'disable_tools': True, 'disable_plan': True, 'category': None},
                           )
        # await self.update_status(room, room.state, player)
        # await self.get_shown_question(room=room, user=user)
        # await self.get_init_model_instructions(
        #     room=room, player=player, should_clear=True, num_steps=-1
        # )
        # await self.show_and_disable_tools(room=room, player=player, update_tools=True)

        await self.log_tool_use(
            room, player, "", dict(), "read_instructions", "start"
        )

    async def toggle_comparison_visibility_dict(self, room: Room, show_comparison: bool):
        """Toggle the visibility of the comparison pane"""
        
        populate_dict = dict()
        if show_comparison:
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
            await room.asave()

            populate_dict = {"populate_comparison_data": {
                    "type": "update_room",
                    "data": {
                        "response_type": "populate_comparison",
                        "question": q_text,
                        "instructions_a": instr_a,
                        "instructions_b": instr_b,
                    },
                }}

        curr_q = await question_from_room(room)
        return populate_dict | {"toggle_comparison_data": {
                "type": "update_room",
                "data": {
                    "response_type": "toggle_comparison",
                    "show_comparison": show_comparison,
                    "got_what_wanted": (room.picked_letter == room.curr_instructions_letter and room.picked_letter in {'A', 'B'}) or 
                    (curr_q.generation_method in {Question.GenerationMethod.ATTENTION_PAIRWISE, Question.GenerationMethod.ATTENTION_SWAP}),
                },
            }}

    async def toggle_comparison_visibility(self, room: Room, show_comparison: bool):
        """Toggle the visibility of the comparison pane"""

        full_data = await self.toggle_comparison_visibility_dict(room, show_comparison)

        if "populate_comparison_data" in full_data:
            """Populate visible information in the comparison pane"""
            await self.channel_layer.group_send(
                self.room_group_name,
                full_data["populate_comparison_data"]
            )

        if "toggle_comparison_data" in full_data:
            await self.channel_layer.group_send(
                self.room_group_name,
                full_data["toggle_comparison_data"]
            )

    async def decide_question_category(self, player: Player):
        """Decide the question category for the player"""

        user = await user_from_player(player)

        # find the unseen math questions
        all_questions_math = Question.objects.filter(
                Q(category=Question.Category.MATH)
                & (
                    Q(generation_method=Question.GenerationMethod.LLAMA)
                    | Q(generation_method=Question.GenerationMethod.QWEN)
                    | Q(generation_method=Question.GenerationMethod.COMMANDR)
                    | Q(generation_method=Question.GenerationMethod.GPT)
                    | Q(generation_method=Question.GenerationMethod.CLAUDE)
                )
            )
        seen_questions_overall_math = AnswerData.objects.filter(
                user=user, category=Question.Category.MATH
            ).values_list("question_id", flat=True)
        unseen_questions_math = all_questions_math.exclude(question_id__in=seen_questions_overall_math)

        # find the unseen trivia questions
        all_questions_trivia = Question.objects.filter(
                Q(category=Question.Category.MULTIHOP)
                & (
                    Q(generation_method=Question.GenerationMethod.LLAMA)
                    | Q(generation_method=Question.GenerationMethod.QWEN)
                    | Q(generation_method=Question.GenerationMethod.COMMANDR)
                    | Q(generation_method=Question.GenerationMethod.GPT)
                    | Q(generation_method=Question.GenerationMethod.CLAUDE)
                )
            )
        seen_questions_overall_trivia = AnswerData.objects.filter(
                user=user, category=Question.Category.MULTIHOP
            ).values_list("question_id", flat=True)
        unseen_questions_trivia = all_questions_trivia.exclude(question_id__in=seen_questions_overall_trivia)

        # decide which question to show
        unseen_math, unseen_trivia = (await unseen_questions_math.acount()), (await unseen_questions_trivia.acount())
        seen_math_all, seen_trivia_all = (await seen_questions_overall_math.acount()), (await seen_questions_overall_trivia.acount())
        if (unseen_math + unseen_trivia) == 0:
            return (
                Question.Category.MULTIHOP
                if random.uniform(0, 1) > 0.5
                else Question.Category.MATH
            )  # pick randomly if no more questions
        if unseen_math == 0:
            return Question.Category.MULTIHOP  # pick trivia if no more math questions
        if unseen_trivia == 0:
            return Question.Category.MATH  # pick math if no more trivia questions
        
        # if they have not seen trivia, show them the trivia tutorial
        if seen_trivia_all == 0:
            return Question.Category.MULTIHOP
        
        # if they have not seen math, show them the trivia tutorial
        if seen_math_all == 0:
            return Question.Category.MATH

        return (
            Question.Category.MULTIHOP
            if random.uniform(0, 1) > 0.5
            else Question.Category.MATH
        )  # random selection otherwise
        
    async def decide_next_question(
        self, room: Room, player: Player, category: Question.Category, is_comparison: bool
    ):
        """Decide the next question to present to the user"""
        # if either category can be shown, decide what the next one should be
        if category == Question.Category.EVERYTHING:
            category = await self.decide_question_category(player)

        user = await user_from_player(player)

        # (question_id, did_comparison) -> number of users who have done it
        question_user_count = AnswerData.objects.filter(
                followed_plan=True, is_final=True, is_report=False
            ).values("question_id", "did_comparison").annotate(user_count=Count("user__user_id", distinct=True))
        question_user_count = await sync_to_async(list)(question_user_count)
        question_to_user_count = {
            (entry["question_id"], entry["did_comparison"]): entry["user_count"]
            for entry in question_user_count
        }

        # questions the user has already seen for this category and experimental group
        seen_questions = AnswerData.objects.filter(
                user=user, category=category, did_comparison=is_comparison
            ).values_list("question_id", flat=True)

        # questions the user has seen overall
        seen_questions_overall = AnswerData.objects.filter(
                user=user, category=category
            ).values_list("question_id", flat=True)

        # check if we need to give a tutorial question or an attention check question
        if (await seen_questions.acount()) == int(os.getenv("NUM_SEEN_FOR_TUTORIAL")):
            return await Question.objects.filter(
                    category=category, generation_method=Question.GenerationMethod.TUTORIAL
                ).afirst()
        elif (await seen_questions.acount()) == int(os.getenv("NUM_SEEN_FOR_ATTENTION")) + 1:
            attention_type = (
                Question.GenerationMethod.ATTENTION_PAIRWISE
                if is_comparison
                else Question.GenerationMethod.ATTENTION_SWAP
            )
            return await Question.objects.filter(
                    category=category, generation_method=attention_type
                ).afirst()

        # otherwise, get the questions that have not been seen
        all_questions = Question.objects.filter(
                Q(category=category)
                & (
                    Q(generation_method=Question.GenerationMethod.LLAMA)
                    | Q(generation_method=Question.GenerationMethod.QWEN)
                    | Q(generation_method=Question.GenerationMethod.COMMANDR)
                    | Q(generation_method=Question.GenerationMethod.GPT)
                    | Q(generation_method=Question.GenerationMethod.CLAUDE)
                )
            )
        all_questions_list = await sync_to_async(list)(all_questions)

        unseen_questions = all_questions.exclude(question_id__in=seen_questions_overall)
        unseen_questions = await sync_to_async(list)(unseen_questions)

        # determine the question limit: for swapping, we need 3 annotations. for pairwise, we need 6 annotations (3 on plan A, 3 on plan B)
        NUM_QUESTIONS_NEEDED = 6 if is_comparison else 3

        # find the questions that almost have this number of annotators
        filtered_questions = [
            question
            for question in unseen_questions
            if question_to_user_count.get((question.question_id, is_comparison), 0)
            < NUM_QUESTIONS_NEEDED
        ]
        filtered_questions.sort(
            key=lambda q: abs(
                NUM_QUESTIONS_NEEDED
                - question_to_user_count.get((q.question_id, is_comparison), 0)
            )
        )

        # if all questions have been annotated
        if len(filtered_questions) == 0:
            if len(unseen_questions) == 0:
                q = random.choice(all_questions_list)
                return q
            else:
                q = random.choice(unseen_questions)
            return q

        return filtered_questions[0]  # return the question closest to being fully annotated

    async def next(self, room: Room, player: Player):
        """Next question"""
        # transition so the user has time to read the instructions
        user = await user_from_player(player)
        if room.state == Room.GameState.IDLE:
            question_type = room.category
            q = await self.decide_next_question(
                room=room,
                player=player,
                category=question_type,
                is_comparison=(await user_from_player(player)).experiment_group == User.ExperimentGroup.PAIRWISE,
            )
            if q is None:  # no questions available D:
                return
            room.current_question = q


            room.steps_seen_a = 1
            room.steps_seen_b = 1
            room.curr_instructions_letter = None
            room.curr_subanswers_a = None
            room.curr_subanswers_b = None
            room.last_guess = None
            room.curr_query = None
            room.curr_query_raw = None
            room.picked_letter = None
            room.search_history = []
            room.history_idx = -1
            room.instruction_map = {}

            await room.asave()
            await self.load_instructions(room=room, player=player)

            # get this logging party started
            await self.log_tool_use(room, player, "", dict(), "question", "start")

            show_comparisons_before = user.experiment_group == User.ExperimentGroup.PAIRWISE
            room.show_comparisons_before = show_comparisons_before

            if show_comparisons_before:
                room.state = Room.GameState.PAIRWISE_COMPARISON
                await room.asave()

                #await self.get_shown_question(room=room, user=user)
                #await self.update_status(room, room.state, player)
                #await self.toggle_comparison_visibility(room=room, show_comparison=True)

                await self.update_ui(room=room, player=player,
                                         show_question_inputs={'user': user},
                                         status_inputs={'status': room.state},
                                         comparison_inputs={'show_comparison': True},
                                         disable_inputs={'update_tools': False, 'disable_tools': False, 'disable_plan': False, 'category': None},
                                         )

                await self.log_tool_use(
                    room, player, "", dict(), "pairwise_comparison", "start"
                )
            else:
                await self.transition_to_instruction(room, player)

        elif room.state in {Room.GameState.INSTRUCTION_READING}:
            room.state = Room.GameState.PLAYING
            room.start_time = timezone.now().timestamp()
            room.end_time = room.start_time + QUESTION_TIME
            await room.asave()

            steps_seen = (
                room.steps_seen_a
                if room.curr_instructions_letter == "A"
                else room.steps_seen_b
            )

            await self.update_ui(room=room, player=player,
                               instr_inputs={'num_steps': steps_seen, 'should_clear': steps_seen == 1},
                               status_inputs={'status': room.state},
                               disable_inputs={'update_tools': False, 'disable_tools': False, 'disable_plan': False, 'category': None},
                               )

            # await self.get_init_model_instructions(
            #     room=room,
            #     player=player,
            #     num_steps=steps_seen,
            #     should_clear=(steps_seen == 1),
            # )
            
            # await self.update_status(room, room.state, player)
            # await self.show_and_disable_tools(
            #     room=room,
            #     player=player,
            #     update_tools=False
            # )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "update_room",
                    "data": await get_room_response_json(room),
                },
            )

            await self.log_tool_use(
                room,
                player,
                "",
                dict(),
                "read_instructions",
                "success",
            )

    async def skip(self, room: Room, player: Player):
        """Skip question while it's playing."""
        current_question = (await question_from_room(room))

        if room.state != Room.GameState.PLAYING or current_question is None:
            return

        if not player.locked_out and room.state == Room.GameState.PLAYING:
            # Quick end question
            room.end_time = room.start_time
            room.buzz_player = None
            room.state = Room.GameState.IDLE
            await room.asave()

    async def buzz_init(self, room: Room, p: Player, guess: str):
        """Initialize buzz"""

        # Reject when not in contest
        if room.state != Room.GameState.PLAYING:
            return

        # Abort if no current question
        if (await question_from_room(room)) is None:
            return

        if not p.locked_out and room.state == Room.GameState.PLAYING:
            room.state = Room.GameState.CONTEST
            room.buzz_player = p
            room.buzz_start_time = timezone.now().timestamp()
            await room.asave()
            await self.update_status(room, room.state, p)

            await create_message("buzz_init", p, None, room)

            await self.send_json(
                {
                    "response_type": "buzz_grant",
                    "guess": guess,
                }
            )
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "update_room",
                    "data": await get_room_response_json(room),
                },
            )

    async def buzz_answer(self, room: Room, player: Player, content):
        """Process a buzz answer"""

        await self.log_tool_use(room, player, "", dict(), "buzz", "start")

        # Reject when not in contest or playing
        if room.state not in {Room.GameState.CONTEST, Room.GameState.PLAYING}:
            return
        
        curr_q = (await question_from_room(room))

        # Abort if no buzz player or current question
        if curr_q is None:
            return

        cleaned_content = clean_content(content)
        answered_correctly = await judge_answer(cleaned_content, curr_q)

        room.last_guess = cleaned_content
        await room.asave()

        if answered_correctly:
            player.score += 10
            player.correct += 1
            await player.asave()

            # Quick end question
            room.end_time = room.start_time
            room.buzz_player = None

            await room.asave()
            await create_message(
                "buzz_correct", player, cleaned_content, room
            )

            await self.log_tool_use(
                room,
                player,
                {"guess": cleaned_content, "true": curr_q.answer_accept},
                {"prediction": answered_correctly},
                "buzz",
                "success",
            )

            room.state = Room.GameState.IDLE
            await room.asave()
            await self.log_leaderboard(room, player)

            # await self.update_status(
            #     room, "buzz_correct", player, cleaned_content
            # )
            # 
            # await self.show_and_disable_tools(room=room, player=player, update_tools=True)

            await self.update_ui(room=room, player=player,
                                     status_inputs={'status': "buzz_correct", 'answer': cleaned_content},
                                     disable_inputs={'update_tools': True, 'disable_tools': True, 'disable_plan': True, 'category': None}
                                     )
        else:
            # Keep playing if it's wrong
            room.state = Room.GameState.PLAYING

            room.buzz_player = None
            await room.asave()

            # Question reading ended, do penalty
            if room.end_time - room.buzz_start_time >= GRACE_TIME:
                player.score -= 10
                player.negs += 1
                await player.asave()

            await create_message(
                "buzz_wrong", player, cleaned_content, room
            )

            buzz_duration = timezone.now().timestamp() - room.buzz_start_time
            room.start_time += buzz_duration
            room.end_time += buzz_duration
            await room.asave()

            await self.log_tool_use(
                room,
                player,
                {"guess": cleaned_content, "true": curr_q.answer_accept},
                {"prediction": answered_correctly},
                "buzz",
                "failure",
            )
            await self.update_status(
                room, "buzz_incorrect", player, cleaned_content
            )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": await get_room_response_json(room),
            },
        )

    async def update_experiment_type(self, user: User):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'update_room',
                'data': {
                    "response_type": "set_experiment_type",
                    "experiment_type": user.experiment_group,
                    "category_preference": user.category_preference,
                    "prefers_auto_scroll": user.auto_scroll,
                },
            }
        )

    async def get_shown_question_dict(self, room: Room, user: User):
        """Computes the correct amount of the question to show, depending on the state of the game."""
        return {"get_shown_question_data": {
                "type": "update_room",
                "data": {
                    "response_type": "get_shown_question",
                    "shown_question": await room.get_shown_question(),
                    "is_tutorial": (await question_from_room(room)).generation_method == Question.GenerationMethod.TUTORIAL,
                    "is_pairwise": user.experiment_group == User.ExperimentGroup.PAIRWISE,
                    "state": room.state,
                },
            }}

    async def get_shown_question(self, room: Room, user: User):
        """Computes the correct amount of the question to show, depending on the state of the game."""
        await self.channel_layer.group_send(
            self.room_group_name,
            (await self.get_shown_question_dict(room, user))["get_shown_question_data"]
        )

    async def decide_instruction_to_show(self, room: Room, player: Player):
        """Decide which instruction the user should see"""

        curr_q = await question_from_room(room)
        user = await user_from_player(player)
        if curr_q.generation_method in {Question.GenerationMethod.ATTENTION_PAIRWISE, Question.GenerationMethod.ATTENTION_SWAP}:
            return "A"

        # if users can swap, give them a random plan, as they can switch to the other one
        if user.experiment_group == User.ExperimentGroup.SWAP:
            is_swapped = random.uniform(0, 1) > 0.5
            room.instruction_map = {'swapped': is_swapped}
            return "B" if is_swapped else "A"

        # otherwise, quantify which one has been seen less and show that one to balance out the labels
        instruction_obj = AnswerData.objects.filter(
            question_id=room.current_question.question_id, did_comparison=True, is_final=True, is_report=False
        )
        seen_instr_A = instruction_obj.filter(final_instructions_letter="A").values("user_id")
        seen_instr_B = instruction_obj.filter(final_instructions_letter="B").values("user_id")

        num_shown_A = await seen_instr_A.distinct().acount()
        num_shown_B = await seen_instr_B.distinct().acount()

        if num_shown_A == num_shown_B:
            return "A" if random.uniform(0, 1) > 0.5 else "B"
        return "A" if num_shown_A < num_shown_B else "B"


    async def decrease_steps(self, room: Room, player: Player, subanswers: List[str]):
        """Decrease the number of steps by 1"""

        await self.log_tool_use(
            room, player, {}, {'curr_subanswers': subanswers}, "decrease_steps", "start"
        )

        if room.curr_instructions_letter == "A":
            room.steps_seen_a -= 1
        elif room.curr_instructions_letter == "B":
            room.steps_seen_b -= 1
        await room.asave()

        await self.log_tool_use(
            room, player, {}, {'curr_subanswers': subanswers[:-1]}, "decrease_steps", "success"
        )

    async def send_subanswers(
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
        if room.curr_instructions_letter is None:
            return

        if room.curr_instructions_letter == "A":
            room.curr_subanswers_a = subanswers
        elif room.curr_instructions_letter == "B":
            room.curr_subanswers_b = subanswers

        await room.asave()
        await room.arefresh_from_db()

        await self.log_answers(
            room=room, 
            player=player,
            is_correct=is_correct, 
            is_final=is_final, 
            followed_plan=followed_plan, 
            true_answer=(await question_from_room(room)).answer_accept, 
            guessed_answer=room.last_guess,
            notes=notes
        )

    async def swap_plan(self, room: Room, player: Player, subanswers: List[str]):
        """Swap the plan for the user"""

        if room.curr_instructions_letter is None:
            return

        old_letter = room.curr_instructions_letter
        await self.log_tool_use(
            room, player, old_letter, {
                'num_steps_seen': room.steps_seen_a if old_letter == "A" else room.steps_seen_b, 
                'curr_subanswers': subanswers
            }, 
            "swap_instructions", "start"
        )

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
        await room.asave()


        await self.updated_swapped_instructions(
            room=room, player=player, num_steps=new_steps, subanswers=new_subanswers
        )

        await self.log_tool_use(
            room, player, old_letter, {
                'num_steps_seen': room.steps_seen_a if swapped_letter == "A" else room.steps_seen_b, 
                'curr_subanswers': [''] if new_subanswers is None else new_subanswers
            }, 
            "swap_instructions", "success"
        )

    async def load_instructions(self, room: Room, player: Player):
        """Load instructions to show to the user"""
        instruction_label = await self.decide_instruction_to_show(room=room, player=player)
        room.curr_instructions_letter = instruction_label
        await room.asave()

    async def show_next_step(self, room: Room, player: Player, subanswers):
        """Show the next step to the user"""
        curr_q = (await question_from_room(room))
        await self.log_tool_use(
            room, player, {}, {'curr_subanswers': subanswers}, "next_step", "start"
        )

        curr_steps = (
            room.steps_seen_a
            if room.curr_instructions_letter == "A"
            else room.steps_seen_b
        )

        curr_instr = (
            curr_q.instructions_a
            if room.curr_instructions_letter == "A"
            else curr_q.instructions_b
        )

        if curr_steps == len(curr_instr["steps"]):
            return

        if room.curr_instructions_letter == "A":
            room.steps_seen_a += 1
        elif room.curr_instructions_letter == "B":
            room.steps_seen_b += 1

        await room.asave()
        curr_steps += 1
        await self.get_init_model_instructions(
            room=room, player=player, num_steps=curr_steps, should_clear=False
        )

        await self.log_tool_use(
            room, player, {}, {'curr_subanswers': subanswers + ['']}, "next_step", "success"
        )

    async def updated_swapped_instructions(
        self, room: Room, player: Player, num_steps: int, subanswers
    ) -> None:
        """After the players are ready for the next question, show them the right instructions"""

        curr_q = (await question_from_room(room))
        instructions_label = room.curr_instructions_letter
        instructions = (
            curr_q.instructions_a
            if instructions_label == "A"
            else curr_q.instructions_b
        )

        # Send instructions only to the player's WebSocket
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "update_swapped_instructions",
                    "instructions": {"steps": instructions["steps"][:num_steps]},
                    "subanswers": subanswers,
                    "is_last_step": num_steps == len(instructions["steps"]),
                    "plan_label": ('B' if room.curr_instructions_letter == 'A' else 'A') if room.instruction_map['swapped'] else room.curr_instructions_letter
                },
            },
        )

    async def clear_instructions(self, room: Room, player: Player):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "clear_instructions",
                },
            },
        )

    async def update_ui(self, room: Room, player: Player, 
                            show_question_inputs: dict = dict(),
                            status_inputs: dict = dict(), 
                            comparison_inputs: dict = dict(),
                            instr_inputs: dict = dict(),
                            disable_inputs: dict = dict(),
                            ):

        show_question_outputs = {'should_run_shown_question': False}
        if show_question_inputs:
            show_question_outputs = show_question_outputs | (await self.get_shown_question_dict(room, show_question_inputs['user']))
            #await self.get_shown_question(room, show_question_inputs['user'])
            show_question_outputs["should_run_shown_question"] = True

        status_outputs = {'should_run_status': False}
        if status_inputs:
            status_outputs = status_outputs | (await self.update_status_dict(room, status_inputs['status'], player, status_inputs.get('answer', '')))
            #await self.update_status(room, status_inputs['status'], player, status_inputs.get('answer', ''))
            status_outputs["should_run_status"] = True

        comparison_outputs = {'should_run_comparison': False}
        if comparison_inputs:
            comparison_outputs = comparison_outputs | (await self.toggle_comparison_visibility_dict(room, comparison_inputs['show_comparison']))
            #await self.toggle_comparison_visibility(room, comparison_inputs['show_comparison'])
            comparison_outputs["should_run_comparison"] = True

        instr_outputs = {'should_run_instr': False}
        if instr_inputs:
            instr_outputs = instr_outputs | (await self.get_init_model_instructions_dict(room, player, instr_inputs['num_steps'], instr_inputs['should_clear']))
            #await self.get_init_model_instructions(room, player, instr_inputs['num_steps'], instr_inputs['should_clear'])
            instr_outputs["should_run_instr"] = True
        
        disable_outputs = {'should_run_disable': False}
        if disable_inputs:
            disable_outputs = disable_outputs | (await self.show_and_disable_tools_dict(room, player, disable_inputs['update_tools'], disable_inputs['disable_tools'], disable_inputs['disable_plan'], disable_inputs['category']))
            #await self.show_and_disable_tools(room, player, disable_inputs['update_tools'])
            disable_outputs["should_run_disable"] = True

        merged_dict = show_question_outputs | status_outputs | comparison_outputs | instr_outputs | disable_outputs
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "update_ui",
                    "full_data": merged_dict,
                }
            },
        )


    async def get_init_model_instructions_dict(
        self, room: Room, player: Player, num_steps: int, should_clear: bool
    ) -> None:
        """After the players are ready for the next question, show them the right instructions"""

        curr_q = (await question_from_room(room))
        instructions = (
            curr_q.instructions_a
            if room.curr_instructions_letter == "A"
            else curr_q.instructions_b
        )

        curr_steps = (
            instructions["steps"]
            if curr_q.generation_method != Question.GenerationMethod.ATTENTION_PAIRWISE
            else instructions["steps_leaked"]
        )

        # Send instructions only to the player's WebSocket
        return {"update_instructions_data": {
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
            }}

    async def get_init_model_instructions(
        self, room: Room, player: Player, num_steps: int, should_clear: bool
    ) -> None:
        """After the players are ready for the next question, show them the right instructions"""

        curr_q = (await question_from_room(room))
        instructions = (
            curr_q.instructions_a
            if room.curr_instructions_letter == "A"
            else curr_q.instructions_b
        )

        curr_steps = (
            instructions["steps"]
            if curr_q.generation_method != Question.GenerationMethod.ATTENTION_PAIRWISE
            else instructions["steps_leaked"]
        )

        # Send instructions only to the player's WebSocket
        await self.channel_layer.group_send(
            self.room_group_name,
            (await self.get_init_model_instructions_dict(room, player, num_steps, should_clear))["update_instructions_data"]
        )

    async def update_tools_and_doc_for_question_and_player(self, room: Room, player: Player):
        """Update the visible tools and document based on the current question for just one player"""
        question = await question_from_room(room)


        """Update the tool"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "update_tools", "use_calculator": (question is None and room.category in {Question.Category.MATH, Question.Category.EVERYTHING}) or (question is not None and question.category == Question.Category.MATH), 
                    "use_doc": False,
                    "use_web": (question is None and room.category in {Question.Category.MULTIHOP}) or (question is not None and question.category == Question.Category.MULTIHOP),
                }
            },
        )

        """Update the document"""
        curr_doc = ""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "update_doc",
                    "use_doc": (question is None and room.category in {Question.Category.MULTIHOP}) or (question is not None and question.category == Question.Category.MULTIHOP),
                    "doc_content": curr_doc,
                },
            },
        )

    async def disable_plan(self):
        """Helper function to disable the plan"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": {
                    "response_type": "disable_plan",
                },
            },
        )

    async def show_and_disable_tools_dict(self, room: Room, player: Player, update_tools: bool, disable_tools: bool, disable_plan: bool, category: None | Question.Category):

        question = (await question_from_room(room))

        if category == None:
            category = question.category

        update_tools_dict = dict()
        update_doc_dict = dict()
        disable_plan_dict = dict()
        disable_tools_dict = dict()

        if (update_tools):
            update_tools_dict = {"update_tools_data": {
                "type": "update_room",
                "data": {
                    "response_type": "update_tools",
                    "use_calculator": category == Question.Category.MATH, 
                    "use_doc": False,
                    "use_web": category == Question.Category.MULTIHOP,
                }
            }}

            curr_doc = ""
            update_doc_dict = {"update_doc_data": {
                    "type": "update_room",
                    "data": {
                        "response_type": "update_doc",
                        "use_doc": category == Question.Category.MULTIHOP,
                        "doc_content": curr_doc,
                    },
                }}

        disable_tools_dict = {"disable_tools_data": {
            "type": "update_room",
            "data": {
                "response_type": "disable_tools",
                "should_disable": disable_tools,
                "should_clear_document": False if not update_tools else (category == Question.Category.MULTIHOP)
            },
        }}

        if disable_plan:
            disable_plan_dict = {"disable_plan_data": {
                    "type": "update_room",
                    "data": {
                        "response_type": "disable_plan",
                    },
                }}

        return update_tools_dict | update_doc_dict | disable_tools_dict | disable_plan_dict


    async def show_and_disable_tools(self, room: Room, player: Player, update_tools: bool, disable_tools: bool, disable_plan: bool, category: None | Question.Category):
        """Update the visible tools and document based on the current question"""

        full_data = await self.show_and_disable_tools_dict(room, player, update_tools, disable_tools, disable_plan, category)

        """Update the tools"""
        if full_data.get("update_tools_data", dict()):
            await self.channel_layer.group_send(
                self.room_group_name,
                full_data["update_tools_data"]
            )

        """Update the document"""
        if full_data.get("update_doc_data", dict()):
            await self.channel_layer.group_send(
                self.room_group_name,
                full_data["update_doc_data"]
            )

        """Helper function to enable/disable the tool buttons"""
        await self.channel_layer.group_send(
            self.room_group_name,
            full_data["disable_tools_data"]
        )

        if full_data.get("disable_plan_data", dict()):
            """Helper function to disable the plan"""
            await self.channel_layer.group_send(
                self.room_group_name,
                full_data["disable_plan_data"]
            )

    async def update_status_dict(self, room: Room, status: str, player: Player, answer=""):
        """Helper function to update the status text"""
        return {"update_status_data": {
                "type": "update_room",
                "data": {
                    "response_type": "update_status",
                    "status": status,
                    "player": (await user_from_player(player)).name,
                    "answer": answer,
                    "allow_swaps": not room.show_comparisons_before,
                },
            }}

    async def update_status(self, room: Room, status: str, player: Player, answer=""):
        """Helper function to update the status text"""
        await self.channel_layer.group_send(
            self.room_group_name,
            (await self.update_status_dict(room, status, player, answer))["update_status_data"]
        )

    async def disable_tool_btns(
        self,
        room: Room,
        player: Player,
        should_disable: bool,
        should_clear_document: bool,
    ):
        """Helper function to enable/disable the tool buttons"""
        await self.channel_layer.group_send(
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


    async def document_loading_page(self, channel_layer_send, player_channel):
        """Helper function to update document info"""
        await channel_layer_send(
            player_channel,
            {
                "type": "update_room",
                "data": {
                    "response_type": "loading_doc",
                },
            },
        )


    async def update_doc(self, channel_layer_send, player_channel, use_doc, doc_content):
        """Helper function to update document info"""
        await channel_layer_send(
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


    async def update_tools(
        self, channel_layer_send, player_channel, use_calc, use_doc, use_web
    ):
        """Helper function to update tool info"""
        await channel_layer_send(
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


    async def chat(self, room, p, content):
        """Send chat message"""

        m = clean_content(content)

        await create_message("chat", p, m, room)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update_room",
                "data": await get_room_response_json(room),
            },
        )


    async def kick(self):
        """Kick banned player"""
        await self.send_json(
            {
                "response_type": "kick",
            }
        )
        await self.channel_layer.group_discard(self.room_name, self.channel_name)


    async def too_many_players(self):
        """Too many players in a room. Cannot join room."""
        await self.send_json(
            {
                "response_type": "too_many_players",
            }
        )
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def report_issue(self, room: Room, p: Player, report_data):
        """User reported an issue"""
        user = await user_from_player(p)
        await ReportIssue.objects.acreate(
            user=user,
            question_id=(await question_from_room(room)).question_id,
            is_bad_question=report_data['is_bad_question'],
            is_bad_instruction=report_data['is_bad_instruction'],
            is_bad_answer_verifier=report_data['is_bad_answer_verifier'],
            is_frustrated=report_data['is_frustrated'],
            feedback=report_data['feedback']
        )
        await self.handle_no_buzz(room, p, True)


    async def skip_plan(self, room: Room, p: Player):
        """User said that the plan was bad"""
        await self.report_issue(room, p, {
            'is_bad_question': False,
            'is_bad_instruction': False,
            'is_bad_answer_verifier': False,
            'is_frustrated': True,
            'feedback': ''
        })


    async def log_answers(
        self, room: Room, player: Player, is_correct: bool, is_final: bool, followed_plan: bool, guessed_answer: str, true_answer: str, notes: str,
    ):
        """Log the user's progress on completing the instructions"""
        curr_q = (await question_from_room(room))
        user = (await user_from_player(player))
        # first, check if the question has already been reported
        num_rep = await ReportIssue.objects.filter(
                user=user, question_id=curr_q.question_id
            ).acount()
        is_report = num_rep > 0

        # if not found, log normally
        await AnswerData.objects.acreate(
            user=user,
            question_id=curr_q.question_id,
            category=curr_q.category,
            final_instructions_letter=room.curr_instructions_letter,
            instructions_a=curr_q.instructions_a,
            instructions_b=curr_q.instructions_b,
            subanswers_a=(
                dict() if room.curr_subanswers_a is None else room.curr_subanswers_a
            ),
            subanswers_b=(
                dict() if room.curr_subanswers_b is None else room.curr_subanswers_b
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

    async def log_leaderboard(self, room: Room, p: Player):
        """Log the stats on this question for the leaderboard"""
        user = p.user
        curr_q = await question_from_room(room)
        # find the last time the user looked at the question
        last_question_call = await ToolLog.objects.filter(
                user_id=user.user_id,
                question_id=curr_q.question_id,
                tool_name="question",
            ).order_by("-queried_at").afirst()

        # get all subsequent tool calls
        if last_question_call:
            tool_calls = ToolLog.objects.filter(
                    user_id=user.user_id,
                    question_id=curr_q.question_id,
                    queried_at__gte=last_question_call.queried_at,
                ).order_by("queried_at")
        else:
            print("ERROR: Question was never logged")
            return

        all_buzzes = tool_calls.filter(tool_name="buzz")
        num_buzzes = (await all_buzzes.acount()) // 2
        num_correct_buzzes = await all_buzzes.filter(tool_execution_status="success").acount()

        correctness = (
            0.0 if num_buzzes == 0 else (1.0 * num_correct_buzzes) / num_buzzes
        )

        # Convert query results to a list for runtime calculations
        tool_calls = await sync_to_async(list)(tool_calls)
        total_time_taken = (
            tool_calls[-1].queried_at - tool_calls[2].queried_at
        ).total_seconds()
        if tool_calls[-1].tool_name == "no_buzz":
            tool_calls_noninstruct = tool_calls[3:-1]
        else:
            tool_calls_noninstruct = tool_calls[3:]

        tool_runtime = sum(
            (
                tool_calls_noninstruct[2 * idx + 1].queried_at
                - tool_calls_noninstruct[2 * idx].queried_at
            ).total_seconds()
            for idx in range(len(tool_calls_noninstruct) // 2)
        )

        await LeaderboardLog.objects.acreate(
            user=p.user,
            question_id=curr_q.question_id,
            correctness_score=correctness,
            total_time_taken=total_time_taken,
            tool_runtime=tool_runtime,
            seconds_taken=(total_time_taken - tool_runtime),
            did_comparison=room.show_comparisons_before,
        )

    async def log_tool_use(
        self,
        room: Room,
        p: Player,
        tool_query: str,
        tool_result: dict,
        tool_name: str,
        status: str,
    ):
        user = await user_from_player(p)
        curr_q = (await question_from_room(room))
        """Log the tool that was used"""
        await ToolLog.objects.acreate(
            user_id=user.user_id,
            question_id=curr_q.question_id,
            instruction_type=room.curr_instructions_letter,
            tool_name=tool_name,
            tool_query=tool_query,
            tool_result=tool_result,
            tool_execution_status=status,
        )


    async def send_web_search_error(self, room: Room, p: Player, query: str, error=""):
        """Handle errors during web search"""

        room.curr_query = None
        room.curr_query_raw = None

        openbracket, closebracket = "{", "}"
        wikipedia_css = """
        <link rel="stylesheet" href="https://en.wikipedia.org/w/load.php?debug=false&lang=en&modules=mediawiki.legacy.shared|mediawiki.skinning.content|mediawiki.skinning.interface&only=styles&skin=vector">
        <link rel="stylesheet" href="https://en.wikipedia.org/w/load.php?debug=false&lang=en&modules=site.styles&only=styles&skin=vector">
        """

        fixed_html_content = f"""
<p>No results found: {error}</p><br /><p>Please try another search query. If the issue persists, please contact <a href='mailto:planstudyumd@gmail.com'>planstudyumd@gmail.com</a> ASAP!</p>
"""
        
        script = """<script>
document.addEventListener("keypress", function (event) {
    if (window.parent && typeof window.parent.handleKeyPress === "function") {
    window.parent.handleKeyPress(event);
    }
});
document.addEventListener("keydown", function (event) {
    if (window.parent && typeof window.parent.handleKeyDown === "function") {
    window.parent.handleKeyDown(event);
    }
});
</script>"""

        final_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{query}</title>
            {wikipedia_css}
            <style>
                body {openbracket}
                font-size: 1.2em; /* Scale up text size by 20% */
                {closebracket}
            </style>
        </head>
        <body>
            <div class="mw-body-content">
                <div class="page-header">
                    <h1>Error Encountered</h1>
                </div>
                {fixed_html_content}
            </div>
            {script}
        </body>
        </html>
        """

        room.search_history = room.search_history + [None]
        room.history_idx += 1
        await room.asave()

        await self.send(text_data=json.dumps({
            'response_type': 'web_search_result',
            'result': final_html,
            'doc_search_query': '',
            'will_retrieve': False,
            "doc_search_query": '',
            "web_search_query": '',
            "select_idxs": [],
            "allow_forwards": False,
            "allow_backwards": room.history_idx != 0,
        }))

        # log tool use
        await self.log_tool_use(room, p, query, {"error": error}, "web_search", "failure")

    async def retrieve_from_document_cache(self, key: str):
        doc =  await Document.objects.filter(doc_id=key).afirst()
        return None if doc == None else doc.document_text

    async def add_to_document_cache(self, key: str, value: str):
        await Document.objects.acreate(doc_id=key, document_text=value)

    async def get_wiki_pages(self, room: Room, p: Player, query):
        """Get the Wikipedia page based on the query"""

        query = await self.clean_query(query)
        await self.log_tool_use(room, p, query, dict(), "web_search", "start")

        cached_query_res = await self.retrieve_from_document_cache(
            "wiki_title_query:" + query
        )
        if cached_query_res is not None:
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

            async with aiohttp.ClientSession() as session:
                async with session.get(google_search_url, params=params) as response:
                    response_data = await response.json()
                    search_results = response_data.get("items", [])
                    if not search_results:
                        return ["Your search returned no Wikipedia pages"], "error"
                    
        except Exception as e:
            return [str(e)], "error"

        return [
            r["title"].replace(" - Wikipedia", "").strip() for r in search_results
        ], "new_search"


    async def extract_elements_from_html(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        elements = soup.find_all(id=re.compile(r"^element-"))
        sentences = []
        for elem in elements:
            sentences.append(elem.text.strip())
        return sentences

    
    async def navigate_history(self, room: Room, p: Player, inc: int):

        await self.log_tool_use(room, p, '', {'curr_search': room.search_history[room.history_idx]},
                                'increase_history' if inc == 1 else 'decrease_history', 'start')

        room.history_idx += inc
        wiki_query, select_idxs, typed_query_web, typed_query_search = room.search_history[room.history_idx]
        room.curr_query = wiki_query
        room.curr_query_raw = typed_query_web

        # edge case where we are coming back from a page error
        if room.search_history[-1] == None:
            room.search_history = room.search_history[:-1]

        await room.asave()
        cached_page_res = await self.retrieve_from_document_cache(
            "wiki_page_query:" + wiki_query
        )
        await self.send(
            text_data=json.dumps(
                {
                    "response_type": "navigate_web_search_result",
                    "html": cached_page_res,
                    "typed_query_web": typed_query_web,
                    "typed_query_search": typed_query_search,
                    "select_idxs": select_idxs,
                    "allow_forwards": room.history_idx != len(room.search_history) - 1,
                    "allow_backwards": room.history_idx > 0,
                }
            )
        )
        await self.log_tool_use(room, p, '', {'curr_search': room.search_history[room.history_idx]},
                        'increase_history' if inc == 1 else 'decrease_history', 'start')

    async def send_web_search_success(
        self,
        room: Room,
        p: Player,
        uncleaned_query: str,
        query: str,
        title: str,
        final_html: str,
        cache_title: bool,
        cache_html: bool,
        is_wiki: bool
    ):
        """Successful web search"""

        user = await user_from_player(p)
        if cache_title:
            await self.add_to_document_cache("wiki_title_query:" + query, title)
        if cache_html:
            await self.add_to_document_cache("wiki_page_query:" + title, final_html)

        await self.log_tool_use(
            room, p, query, title, "web_search_hyperlink" if is_wiki else "web_search", "success"
        )

        await self.send(
            text_data=json.dumps(
                {
                    "response_type": "web_search_result",
                    'web_search_query': room.curr_query_raw,
                    'doc_search_query': uncleaned_query if user.auto_scroll and not is_wiki else '',
                    "result": final_html,
                    "allow_forwards": False,
                    "allow_backwards": room.history_idx >= 0,
                    'will_retrieve': (user.auto_scroll and not is_wiki),
                }
            )
        )

        # auto-scroll to the relevant sentence
        if not is_wiki and user.auto_scroll:
            idxs = await self.select_content(room, p, query, final_html)
            new_history_elem = (room.curr_query, idxs, room.curr_query_raw, room.curr_query_raw)
        else:
            new_history_elem = (room.curr_query, [], room.curr_query_raw, '')

        # handle the edge case where we just came from an error
        if room.history_idx != -1 and room.search_history[room.history_idx] == None:
            room.search_history[room.history_idx] = new_history_elem
        else:
            room.search_history = room.search_history[:room.history_idx+1] + [new_history_elem]
            room.history_idx += 1
        await room.asave()
            

    async def get_html_sentences(self, p_tag_input):
        children = []
        for c in p_tag_input.children:
            if c.name == 'sup':
                continue
            elif c.name in ['i', 'b']:
                children.append(c)
            elif c.name in ['a'] and c.get('href') and c.get('href').startswith('/wiki/') and ':' not in c.get('href'):
                children.append(c)
            else:
                children.append(c.text)

        merged_children = []
        for idx, child in enumerate(children):
            if isinstance(child, str):
                if not merged_children or not isinstance(merged_children[-1], str):
                    merged_children.append(child)
                else:
                    merged_children[-1] += child
            else:
                merged_children.append(child)

        merged_children = [(str(c), c if isinstance(c, str) else c.text) for c in merged_children]

        sentences = [s + ' ' for s in nltk.sent_tokenize(''.join([c[1] for c in merged_children]))]

        child_ptr, sentence_ptr, curr_len = 0, 0, 0
        sent_builder = ['']

        while child_ptr < len(merged_children) and sentence_ptr < len(sentences):
            child, child_text = merged_children[child_ptr]
            sentence = sentences[sentence_ptr]

            if curr_len + len(child_text) < len(sentence):
                curr_len += len(child_text)
                sent_builder[-1] += child
                child_ptr += 1
            else:
                prefix, suffix = child_text[:len(sentence) - curr_len], child_text[len(sentence) - curr_len:]
                sent_builder[-1] += prefix
                sent_builder.append("")
                curr_len = 0
                merged_children[child_ptr] = (child.replace(child_text, suffix), suffix)
                sentence_ptr += 1

        return sentences, sent_builder
 
    async def navigate_hyperlink(self, room: Room, p: Player, wiki_url: str):
        wiki_url = wiki_url.replace('/wiki/', '').strip()
        await self.web_search(room, p, wiki_url, True, True)

    async def web_search(self, room: Room, p: Player, query, is_wiki, use_headers):
        """Perform a web search"""

        if is_wiki:
            wiki_pages = [query]
            status = "from_hyperlink"
            await self.log_tool_use(room, p, query, dict(), "web_search_hyperlink", "start")
        else:
            wiki_pages, status = await self.get_wiki_pages(room, p, query)
            if status == "error":
                await self.send_web_search_error(room, p, query, wiki_pages[0])
                return

        for page_title in wiki_pages:
            page_title_clean = page_title

            room.curr_query = page_title_clean
            room.curr_query_raw = query.replace('_', ' ') if is_wiki else query

            cached_page_res = await self.retrieve_from_document_cache(
                "wiki_page_query:" + page_title_clean
            )

            if cached_page_res is not None:
                await self.send_web_search_success(
                    room=room,
                    p=p,
                    uncleaned_query=query,
                    query=await self.clean_query(query),
                    title=page_title_clean,
                    final_html=cached_page_res,
                    cache_title=(status == "new_search"),
                    cache_html=False,
                    is_wiki=is_wiki,
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
                rand_idx = random.choice(list(range(0, 3)))
                WIKI_TOKENS = [os.getenv(f'WIKIMEDIA_API_KEY{token_num}') for token_num in range(1, 4)]
                USER_AGENTS = [os.getenv(f'USER_AGENT{token_num}')  for token_num in range(1, 4)]
                wiki_token, user_agent = WIKI_TOKENS[rand_idx], USER_AGENTS[rand_idx]
                headers = {
                    "Authorization": f"Bearer {wiki_token}",
                    "User-Agent": user_agent,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url, params=params, headers=headers if use_headers else {}) as response:
                        if response.status == 403 or response.headers.get(
                            "mediawiki-api-error", ""
                        ) == "mwoauth-invalid-authorization-invalid-user":
                            await EmergencyWarning.objects.acreate(
                                note=f"Wikimedia key throwing error.\nKey: {rand_idx}\nAgent: {rand_idx}"
                            )
                        if response.status == 200:
                            data = await response.json()

                            if "error" in data:
                                if use_headers and "invalid" in data["error"]["info"] or "forbidden" in data["error"]["info"]:
                                    await EmergencyWarning.objects.acreate(
                                        note=f"Wikimedia key throwing error.\nKey: {str(rand_idx)}"
                                    )
                                    await self.web_search(room, p, query, is_wiki, False)
                                else:
                                    await self.send_web_search_error(room, p, query, data["error"]["info"])
                                return

                            html_content = data["parse"]["text"]["*"]
                            title = data["parse"]["title"]
                            soup = BeautifulSoup(html_content, "html.parser")

                            curr_html = ""
                            element_counter = 0
                            for p_tag in soup.find_all("p"):
                                sentences, html_sentences = await self.get_html_sentences(p_tag)
                                curr_html = ""
                                for sent in html_sentences:
                                    if sent:
                                        curr_html += (
                                            f'<span id="element-{element_counter}">{sent}</span> '
                                        )
                                        element_counter += 1
                                p_tag.clear()
                                p_tag.append(BeautifulSoup(curr_html, "html.parser"))

                            fixed_html_content = str(soup)
                            openbracket, closebracket = "{", "}"
                            wikipedia_css = """
                            <link rel="stylesheet" href="https://en.wikipedia.org/w/load.php?debug=false&lang=en&modules=mediawiki.legacy.shared|mediawiki.skinning.content|mediawiki.skinning.interface&only=styles&skin=vector">
                            <link rel="stylesheet" href="https://en.wikipedia.org/w/load.php?debug=false&lang=en&modules=site.styles&only=styles&skin=vector">
                            """

                            script = """<script>
                            document.addEventListener("keypress", function (event) {
                                if (window.parent && typeof window.parent.handleKeyPress === "function") {
                                window.parent.handleKeyPress(event);
                                }
                            });
                            document.addEventListener("keydown", function (event) {
                                if (window.parent && typeof window.parent.handleKeyDown === "function") {
                                window.parent.handleKeyDown(event);
                                }
                            });
                            </script>"""

                            final_html = f"""
                            <html>
                            <head>
                                <meta charset="UTF-8">
                                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                <title>{title}</title>
                                {wikipedia_css}
                                <style>
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
                                {script}
                            </body>
                            
                            </html>
                            """
                            await self.send_web_search_success(
                                room=room,
                                p=p,
                                uncleaned_query=query,
                                query=await self.clean_query(query),
                                title=page_title_clean,
                                final_html=final_html,
                                cache_title=(status == "new_search"),
                                cache_html=True,
                                is_wiki=is_wiki,
                            )
                            return

            except Exception as e:
                traceback.print_exc()
                continue

        await self.send_web_search_error(room, p, query, "The specified page does not exist")


    async def log_comparison(self, room: Room, p: Player, chosen: str):
        """Log pairwise comparison of instructions"""
        user = await user_from_player(p)
        chosen_adjusted = chosen
        if chosen_adjusted not in {"Tie", "None"} and room.instruction_map["swapped"]:
            chosen_adjusted = "A" if chosen == "B" else "B"
        await ComparisonFeedback.objects.acreate(
            question=(await question_from_room(room)),
            user=user,
            chosen=chosen,
            chosen_adjusted=chosen_adjusted,
            chosen_instruction=(
                chosen if chosen in {"Tie", "None"} else room.instruction_map[chosen]
            ),
            shown_first=room.show_comparisons_before,
        )

        room.state = Room.GameState.PLAYING
        room.start_time = timezone.now().timestamp()
        room.end_time = room.start_time + QUESTION_TIME
        room.picked_letter = chosen_adjusted
        await room.asave()

        #await self.toggle_comparison_visibility(room=room, show_comparison=False)
        #await self.show_and_disable_tools(room=room, player=p, update_tools=True)

        steps_seen = (
            room.steps_seen_a
            if room.curr_instructions_letter == "A"
            else room.steps_seen_b
        )

        await self.update_ui(room=room, player=p,
                            instr_inputs={'num_steps': steps_seen, 'should_clear': steps_seen == 1},
                            status_inputs={'status': room.state},
                            disable_inputs={'update_tools': True, 'disable_tools': False, 'disable_plan': False, 'category': None},
                            comparison_inputs={'show_comparison': False}
                            )
        await self.log_tool_use(room, p, "", dict(), "pairwise_comparison", "success")

    @sync_to_async
    def clean_query(self, query):
        """Clean the query for cached lookup"""
        cleaned_query = re.sub(r"[^a-zA-Z0-9\s\-]", "", query)
        cleaned_query = re.sub(r"\s+", "-", cleaned_query.strip())
        return cleaned_query.lower()

    async def select_content_wrapper(self, room: Room, p: Player, query: str):
        """ Wrapper for long-context content selection """

        curr_q = (await question_from_room(room))
        # If current document doesn't exist
        if (curr_q.category == Question.Category.LONGCONTEXT and not curr_q.document_context) or (not room.curr_query):
            return
        
        search_query = 'long_context:' + curr_q.document_context if (curr_q.category == Question.Category.LONGCONTEXT) else 'wiki_page_query:' + room.curr_query
        html = await self.retrieve_from_document_cache(search_query)

        idxs = await self.select_content(room, p, query, html)
        room.search_history = room.search_history[:room.history_idx+1] + [(room.curr_query, idxs, room.curr_query_raw, query)]
        room.history_idx += 1
        await room.asave()

    async def select_content(self, room: Room, p: Player, query: str, html: str):
        """Executes the content selection tool"""

        await self.log_tool_use(room, p, query, dict(), "content_selection", "start")
        docs = await self.extract_elements_from_html(html)

        cohere_client = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

        try:
            retr_results = await sync_to_async(cohere_client.rerank)(
                model="rerank-english-v3.0",
                query=query,
                documents=docs,
                top_n=1,
                return_documents=True,
            )
        except Exception as e:
            traceback.print_exc()
            await self.send(
                text_data=json.dumps(
                    {
                        "response_type": "content_selection_result",
                        "result": [],
                        "num_docs": 0,
                    }
                )
            )
            await self.log_tool_use(
                room, p, query, {"error": str(e)}, "content_selection", "failure"
            )
            return

        retr_docs = [d.document.text for d in retr_results.results]
        retr_docs = [re.sub(r"\[.*?\]", " ", doc) for doc in retr_docs]
        retr_docs = [re.sub(r"\s+", " ", doc).strip() for doc in retr_docs]
        doc_idxs = [int(d.index) for d in retr_results.results]

        await self.log_tool_use(
            room,
            p,
            query,
            {"retrieved_docs": retr_docs, "doc_idxs": doc_idxs},
            "content_selection",
            "success",
        )

        # Send the retrieved content back to the frontend
        await self.send(
            text_data=json.dumps(
                {
                    "response_type": "content_selection_result",
                    "result": doc_idxs,
                    "num_docs": len(docs),
                    "allow_forwards": False,
                    "allow_backwards": len(room.search_history) > 0
                }
            )
        )

        return doc_idxs


    async def calculate(self, room: Room, p: Player, equation):
        """Executes the calculator tool using SymPy with implicit multiplication handling"""
        await self.log_tool_use(room, p, equation, dict(), "calculator", "start")

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
            await self.log_tool_use(
                room, p, equation, {"calculation": result}, "calculator", "success"
            )

            await self.send(
                text_data=json.dumps(
                    {"response_type": "calculation_result", "result": result}
                )
            )

        except (SympifyError, TypeError, ValueError) as e:
            # Log tool use with error
            await self.log_tool_use(
                room, p, equation, {"error": str(e)}, "calculator", "failure"
            )

            await self.send(
                text_data=json.dumps(
                    {"response_type": "calculation_result", "result": "ERROR"}
                )
            )

    async def handle_no_buzz(self, room: Room, player: Player, is_report: bool):
        """Handles no buzz or report actions"""
        curr_q = await question_from_room(room)
        if room.state == Room.GameState.PLAYING:
            if is_report:
                await self.log_tool_use(room, player, "", dict(), "report", "start")
            else:
                await self.log_tool_use(room, player, "", dict(), "no_buzz", "start")
                await self.log_leaderboard(room, player)

            room.state = Room.GameState.IDLE
            await room.asave()

            curr_answer = curr_q.answer_accept[0]
            await self.update_ui(room=room, player=player,
                               status_inputs={'status': room.state, 'answer': curr_answer},
                               instr_inputs={'num_steps': -1, 'should_clear': True},
                               disable_inputs={'update_tools': True, 'disable_tools': True, 'disable_plan': True, 'category': None}
                               )

            # await self.update_status(room, room.state, player, curr_answer)
            # await self.get_init_model_instructions(
            #     room=room, player=player, num_steps=-1, should_clear=True
            # )
            # await self.show_and_disable_tools(room=room, player=player, update_tools=True)

@sync_to_async
def user_from_player(player):
    return player.user

@sync_to_async
def question_from_room(room):
    return room.current_question

async def get_room_response_json(room):
    """Generates JSON for update response"""
    curr_q = (await question_from_room(room))
    return {
        "response_type": "update",
        "game_state": room.state,
        "current_time": timezone.now().timestamp(),
        "start_time": room.start_time,
        "end_time": room.end_time,
        "buzz_start_time": room.buzz_start_time,
        "category": (
            curr_q.category if curr_q is not None else ""
        ),
        "room_category": room.category,
        "messages": await room.get_messages(),
        "difficulty": room.difficulty,
        "speed": room.speed,
        "players": await room.get_players_by_score(),
        "instruction_map": room.instruction_map,
        "change_locked": room.change_locked,
    }

def get_instructions_response_json(instructions: json) -> Dict:
    return dict(instructions)

def get_question_feedback_response_json(feedback: QuestionFeedback) -> Dict:
    feedback_json = serialize("json", [feedback])
    feedback_dict = json.loads(feedback_json)[0]["fields"]
    return feedback_dict

@sync_to_async
def create_message(tag, p, content, room):
    """Adds a message to db"""
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


def get_or_create_expt_group(user: User):
    if user.experiment_group is not None:
        return (user.experiment_group, False)
    
    # (question_id, did_comparison) -> number of users who have done it
    question_to_user_count = dict()
    all_entries = AnswerData.objects.filter(is_final=True, is_report=False).values("question_id", "did_comparison").annotate(user_count=Count("user__user_id", distinct=True))
    all_entries = all_entries
    for entry in all_entries:
        question_to_user_count[(entry["question_id"], entry["did_comparison"])] = entry["user_count"]

    num_swap_questions_done = 0
    num_pairwise_questions_done = 0
    for k, v in question_to_user_count.items():
        if k[1]:
            num_pairwise_questions_done += int(v >= 6)
        else:
            num_swap_questions_done += int(v >= 3)
    
    num_swap_users = User.objects.filter(experiment_group=User.ExperimentGroup.SWAP).count()
    num_pairwise_users = User.objects.filter(experiment_group=User.ExperimentGroup.PAIRWISE).count()

    if num_swap_questions_done == num_pairwise_questions_done:
        if num_swap_users * 2 < num_pairwise_users:
            return (User.ExperimentGroup.SWAP, True)
        elif num_pairwise_users < num_swap_users * 2:
            return (User.ExperimentGroup.PAIRWISE, True)
        else:
            return (
                (User.ExperimentGroup.PAIRWISE, True)
                if random.uniform(0, 1) > 0.33
                else (User.ExperimentGroup.SWAP, True)
            )
    elif num_swap_questions_done > num_pairwise_questions_done:
        return (User.ExperimentGroup.PAIRWISE, True)
    else:
        return (User.ExperimentGroup.SWAP, True)