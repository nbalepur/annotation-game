import pytest
from .models import *
from .consumers import QuizbowlConsumer 

from unittest.mock import patch
from game.models import Room, Question, AnswerData, Player, User
from game.consumers import QuizbowlConsumer

import pytest
from unittest.mock import patch
from game.models import Room, Question, AnswerData, Player, User
from game.consumers import QuizbowlConsumer
import random
from django.test import override_settings

@pytest.mark.django_db
class TestConsumers:
    def setup_method(self):
        # Create test data

        question = Question.objects.create(
                question_id=1,
                generation_method=Question.GenerationMethod.LLAMA,
                category=Question.Category.MATH,
                content="What is the square root of 16? Four is the answer.",
                clue_list=["What is the square root of 16?", "Four is the answer."],
                length=2
        )
        question.save()

        self.room = Room.objects.create(
            current_question=question
        )
        self.user = User.objects.create(name="testuser", user_id=1000)
        self.player = Player.objects.create(user=self.user, room=self.room)

        self.all_users = [User.objects.create(user_id=idx, name=f"user{idx}") for idx in range(10)]

        self.extra_questions = [
            Question.objects.create(
                question_id=idx,
                generation_method=Question.GenerationMethod.LLAMA,
                category=Question.Category.MULTIHOP
            )
            for idx in range(1234, 1334)
        ]

        for flag in [True, False]:
            for q in self.extra_questions:
                AnswerData.objects.create(
                    user=self.user,
                    question_id=q.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=flag,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

    def test_decide_instruction_to_show_attention_methods(self):
        """Test when generation method is ATTENTION_PAIRWISE or ATTENTION_SWAP."""
        consumer = QuizbowlConsumer()

        # ATTENTION_PAIRWISE
        self.room.current_question.generation_method = Question.GenerationMethod.ATTENTION_PAIRWISE
        assert consumer.decide_instruction_to_show(self.room) == "A"

        # ATTENTION_SWAP
        self.room.current_question.generation_method = Question.GenerationMethod.ATTENTION_SWAP
        assert consumer.decide_instruction_to_show(self.room) == "A"

    def test_decide_instruction_to_show_swap_distribution(self):
        """Test when SETTING_TYPE is 'swap'."""
        consumer = QuizbowlConsumer()
        with patch.dict("os.environ", {"SETTING_TYPE": "swap"}):
            # Should follow the mocked random.uniform values
            self.room.current_question.generation_method = Question.GenerationMethod.LLAMA
            out = []
            for _ in range(1000):
                out.append(consumer.decide_instruction_to_show(self.room))
            sum_a = sum([o == 'A' for o in out])
            assert 450 <= sum_a <= 550

    def test_decide_instruction_to_show_pairwise_balancing(self):
        """Test when SETTING_TYPE is 'pairwise'."""
        consumer = QuizbowlConsumer()
        with patch.dict("os.environ", {"SETTING_TYPE": "pairwise"}):
            self.room.current_question.generation_method = Question.GenerationMethod.LLAMA

            # Create AnswerData with more "B" instances
            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[0],
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="B",
            )

            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[1],
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="B",
            )

            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[2],
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )
            # Should return "A" because "A" has been seen less
            for _ in range(1000):
                assert consumer.decide_instruction_to_show(self.room) == "A"

            # Add another "A" to balance
            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[3],
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

            out = []
            for _ in range(1000):
                out.append(consumer.decide_instruction_to_show(self.room))
            sum_a = sum([o == 'A' for o in out])
            assert 450 <= sum_a <= 550

            # Add another "A" to make it uneven again
            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[4],
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )
            for _ in range(50):
                assert consumer.decide_instruction_to_show(self.room) == "B"

    def test_report(self):

        consumer = QuizbowlConsumer()

        with patch.dict("os.environ", {"SETTING_TYPE": "pairwise"}):

            """Test that we ignore reported questions"""
            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[0],
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="B",
            )

            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[0],
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                is_report=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[0],
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                is_report=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

            for _ in range(50):
                assert consumer.decide_instruction_to_show(self.room) == "A"


@pytest.mark.django_db
class TestConsumersTrivia:
    def setup_method(self):
        # Create test data

        question = Question.objects.create(
                question_id=1,
                generation_method=Question.GenerationMethod.LLAMA,
                category=Question.Category.MULTIHOP,
                content="What is the square root of 16? Four is the answer.",
                clue_list=["What is the square root of 16?", "Four is the answer."],
                length=2
        )
        question.save()

        self.room = Room.objects.create(
            current_question=question
        )
        self.user = User.objects.create(name="testuser", user_id=1000)
        self.player = Player.objects.create(user=self.user, room=self.room)

        self.all_users = [User.objects.create(user_id=idx, name=f"user{idx}") for idx in range(10)]

        self.extra_questions = [
            Question.objects.create(
                question_id=idx,
                generation_method=Question.GenerationMethod.LLAMA,
                category=Question.Category.MATH
            )
            for idx in range(1234, 1334)
        ]

        for flag in [True, False]:
            for q in self.extra_questions:
                AnswerData.objects.create(
                    user=self.user,
                    question_id=q.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=flag,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

    def test_decide_instruction_to_show_attention_methods(self):
        """Test when generation method is ATTENTION_PAIRWISE or ATTENTION_SWAP."""
        consumer = QuizbowlConsumer()

        # ATTENTION_PAIRWISE
        self.room.current_question.generation_method = Question.GenerationMethod.ATTENTION_PAIRWISE
        assert consumer.decide_instruction_to_show(self.room) == "A"

        # ATTENTION_SWAP
        self.room.current_question.generation_method = Question.GenerationMethod.ATTENTION_SWAP
        assert consumer.decide_instruction_to_show(self.room) == "A"

    def test_decide_instruction_to_show_swap_distribution(self):
        """Test when SETTING_TYPE is 'swap'."""
        consumer = QuizbowlConsumer()
        with patch.dict("os.environ", {"SETTING_TYPE": "swap"}):
            # Should follow the mocked random.uniform values
            self.room.current_question.generation_method = Question.GenerationMethod.LLAMA
            out = []
            for _ in range(1000):
                out.append(consumer.decide_instruction_to_show(self.room))
            sum_a = sum([o == 'A' for o in out])
            assert 450 <= sum_a <= 550

    def test_decide_instruction_to_show_pairwise_balancing(self):
        """Test when SETTING_TYPE is 'pairwise'."""
        consumer = QuizbowlConsumer()
        with patch.dict("os.environ", {"SETTING_TYPE": "pairwise"}):
            self.room.current_question.generation_method = Question.GenerationMethod.LLAMA

            # Create AnswerData with more "B" instances
            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[0],
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="B",
            )

            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[1],
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="B",
            )

            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[2],
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )
            # Should return "A" because "A" has been seen less
            for _ in range(1000):
                assert consumer.decide_instruction_to_show(self.room) == "A"

            # Add another "A" to balance
            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[3],
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

            out = []
            for _ in range(1000):
                out.append(consumer.decide_instruction_to_show(self.room))
            sum_a = sum([o == 'A' for o in out])
            assert 450 <= sum_a <= 550

            # Add another "A" to make it uneven again
            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[4],
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )
            for _ in range(50):
                assert consumer.decide_instruction_to_show(self.room) == "B"

    def test_report(self):

        consumer = QuizbowlConsumer()

        with patch.dict("os.environ", {"SETTING_TYPE": "pairwise"}):

            """Test that we ignore reported questions"""
            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[0],
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[0],
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                is_report=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="B",
            )

            AnswerData.objects.create(
                question_id=self.room.current_question.question_id,
                user=self.all_users[0],
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=False,
                is_correct=True,
                is_final=True,
                is_report=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="B",
            )

            for _ in range(50):
                assert consumer.decide_instruction_to_show(self.room) == "B"

@pytest.mark.django_db
class TestDecideNextQuestion:
    def setup_method(self):
        # Create test data
        self.consumer = QuizbowlConsumer()

        self.room = Room.objects.create()
        self.user = User.objects.create(name="testuser", user_id=1000)
        self.player = Player.objects.create(user=self.user, room=self.room)

        # Create tutorial, sanity, and regular questions
        self.tutorial_question = Question.objects.create(
            question_id=1,
            generation_method=Question.GenerationMethod.TUTORIAL,
            category=Question.Category.MATH
        )

        self.sanity_question = Question.objects.create(
            question_id=2,
            generation_method=Question.GenerationMethod.ATTENTION_PAIRWISE,
            category=Question.Category.MATH
        )

        self.sanity_question_swap = Question.objects.create(
            question_id=2000,
            generation_method=Question.GenerationMethod.ATTENTION_SWAP,
            category=Question.Category.MATH
        )

        self.regular_questions = [
            Question.objects.create(
                question_id=idx,
                generation_method=Question.GenerationMethod.LLAMA,
                category=Question.Category.MATH
            )
            for idx in range(3, 20)
        ]

        self.extra_questions = [
            Question.objects.create(
                question_id=idx,
                generation_method=Question.GenerationMethod.LLAMA,
                category=Question.Category.MULTIHOP
            )
            for idx in range(100, 200)
        ]

        for flag in [True, False]:
            for q in self.extra_questions:
                AnswerData.objects.create(
                    user=self.user,
                    question_id=q.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=flag,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

    def test_tutorial_question(self):
        """If the user has seen 0 questions, return the tutorial question."""
        with patch.dict("os.environ", {"NUM_SEEN_FOR_TUTORIAL": "0"}):
            for flag in [True, False]:
                next_question = self.consumer.decide_next_question(
                    self.room, self.player, Question.Category.MATH, flag
                )
                assert next_question == self.tutorial_question

    def test_sanity_question(self):
        """If the user has seen 7 questions, return the sanity question."""

        for question in self.regular_questions[:7]:
            AnswerData.objects.create(
                user=self.user,
                question_id=question.question_id,
                category=Question.Category.MATH,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )
        AnswerData.objects.create(
            user=self.user,
            question_id=self.tutorial_question.question_id,
            category=Question.Category.MATH,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=True,
            followed_plan=True,
            is_correct=True,
            is_final=True
        )

        for question in self.regular_questions[-7:]:
            AnswerData.objects.create(
                user=self.user,
                question_id=question.question_id,
                category=Question.Category.MATH,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )

        AnswerData.objects.create(
            user=self.user,
            question_id=self.tutorial_question.question_id,
            category=Question.Category.MATH,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=False,
            followed_plan=True,
            is_correct=True,
            is_final=True
        )

        # next_question = self.consumer.decide_next_question(
        #     self.room, self.player, Question.Category.MATH, True
        # )
        # assert next_question == self.sanity_question

        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MATH, False
        )
        assert next_question == self.sanity_question_swap

    def test_last_unseen_question(self):
        """If the user has seen n - 1 questions, return the last unseen question."""
        for flag in [True, False]:
            for question in self.regular_questions[:-1]:
                AnswerData.objects.create(
                    user=self.user,
                    question_id=question.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=flag,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MATH, True
        )
        assert next_question == self.regular_questions[-1]

        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MATH, False
        )
        assert next_question == self.regular_questions[-1]

    def test_unseen_questions_split(self):
        """Ensure we only schedule unseen questions"""
        for flag in [True, False]:
            seen_ids = set()
            for question in self.regular_questions[:7]:
                AnswerData.objects.create(
                    user=self.user,
                    question_id=question.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=flag,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )
                seen_ids.add(question.question_id)

            for _ in range(100):
                next_question = self.consumer.decide_next_question(
                    self.room, self.player, Question.Category.MATH, flag
                )
                assert next_question.question_id not in seen_ids

    def test_annotation_based_question(self):
        """Return the question with between 1 and 6 annotations over 0 or more than 5 (pairwise setting)."""

        overflow_questions = self.regular_questions[:5]
        return_question = self.regular_questions[7]
        question_seen = self.regular_questions[5]
        return_question_less = self.regular_questions[6]
        zero_questions = self.regular_questions[8:]

        # ======================================== PAIRWISE SETTING TYPE ========================================

        AnswerData.objects.create(
            user=self.user,
            question_id=question_seen.question_id,
            category=Question.Category.MATH,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=True,
            followed_plan=True,
            is_correct=True,
            is_final=True
        )

        with override_settings(SETTING_TYPE="pairwise"):

            # set up questions that overflowed
            for question in overflow_questions:
                num_annot = random.randint(6, 10)
                for epoch in range(num_annot):
                    curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
                    AnswerData.objects.create(
                        user=curr_user,
                        question_id=question.question_id,
                        category=Question.Category.MATH,
                        final_instructions_letter="A",
                        instructions_a={},
                        instructions_b={},
                        subanswers_a={},
                        subanswers_b={},
                        steps_seen_a=1,
                        steps_seen_b=1,
                        did_comparison=True,
                        followed_plan=True,
                        is_correct=True,
                        is_final=True
                    )

            # questions with 1 to 5 (inclusive) diff users who have looked at it
            for epoch in range(1, 6):
                curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")

                if epoch != 1:
                    AnswerData.objects.create(
                            user=curr_user,
                            question_id=return_question_less.question_id,
                            category=Question.Category.MATH,
                            final_instructions_letter="A",
                            instructions_a={},
                            instructions_b={},
                            subanswers_a={},
                            subanswers_b={},
                            steps_seen_a=1,
                            steps_seen_b=1,
                            did_comparison=True,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True
                        )
                AnswerData.objects.create(
                        user=curr_user,
                        question_id=return_question.question_id,
                        category=Question.Category.MATH,
                        final_instructions_letter="A",
                        instructions_a={},
                        instructions_b={},
                        subanswers_a={},
                        subanswers_b={},
                        steps_seen_a=1,
                        steps_seen_b=1,
                        did_comparison=True,
                        followed_plan=True,
                        is_correct=True,
                        is_final=True
                    )
                AnswerData.objects.create(
                        user=curr_user,
                        question_id=question_seen.question_id,
                        category=Question.Category.MATH,
                        final_instructions_letter="A",
                        instructions_a={},
                        instructions_b={},
                        subanswers_a={},
                        subanswers_b={},
                        steps_seen_a=1,
                        steps_seen_b=1,
                        did_comparison=True,
                        followed_plan=True,
                        is_correct=True,
                        is_final=True
                    )
        
                next_question = self.consumer.decide_next_question(
                    self.room, self.player, Question.Category.MATH, True
                )
                assert next_question == return_question

        epoch = 6
        curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
        AnswerData.objects.create(
                user=curr_user,
                question_id=return_question.question_id,
                category=Question.Category.MATH,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )
        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MATH, True
        )
        assert next_question == return_question_less

        # ======================================== SWAP SETTING TYPE ========================================

    def test_annotation_based_question_swap(self):
        """Return the question with between 1 and 3 annotations over 0 or more than 3 (swap setting)."""

        overflow_questions = self.regular_questions[:5]
        return_question = self.regular_questions[7]
        question_seen = self.regular_questions[5]
        return_question_less = self.regular_questions[6]
        zero_questions = self.regular_questions[8:]

        AnswerData.objects.create(
            user=self.user,
            question_id=question_seen.question_id,
            category=Question.Category.MATH,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=False,
            followed_plan=True,
            is_correct=True,
            is_final=True
        )

        # set up questions that overflowed
        for question in overflow_questions:
            num_annot = random.randint(3, 10)
            for epoch in range(num_annot):
                curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=question.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

        # questions with 1 to 5 (inclusive) diff users who have looked at it
        for epoch in range(1, 3):
            curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")

            if epoch != 1:
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=return_question_less.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

            AnswerData.objects.create(
                    user=curr_user,
                    question_id=return_question.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )
            AnswerData.objects.create(
                    user=curr_user,
                    question_id=question_seen.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )
    
            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MATH, False
            )
            assert next_question == return_question

        epoch = 3
        curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
        AnswerData.objects.create(
                user=curr_user,
                question_id=return_question.question_id,
                category=Question.Category.MATH,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )
        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MATH, False
        )
        assert next_question == return_question_less

    def test_seen_all_and_all_annotated(self):

        for question in self.regular_questions:
            for epoch in range(20):
                curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=question.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )
            AnswerData.objects.create(
                user=self.user,
                question_id=question.question_id,
                category=Question.Category.MATH,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )

        all_questions = set()
        for _ in range(1000):
            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MATH, False
            )
            all_questions.add(next_question.question_id)

        assert all_questions == set([q.question_id for q in self.regular_questions])

    def test_all_annotated_but_some_unseen(self):

        for question in self.regular_questions:
            for epoch in range(20):
                curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=question.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

        for question in self.regular_questions[:-5]:
            AnswerData.objects.create(
                user=self.user,
                question_id=question.question_id,
                category=Question.Category.MATH,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )

        all_questions = set()
        for _ in range(1000):
            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MATH, False
            )
            all_questions.add(next_question.question_id)

        assert all_questions == set([q.question_id for q in self.regular_questions[-5:]])

    def test_report_unannotated_question(self):
        """Ensure reported questions are not counted in the annotation."""

        overflow_questions = self.regular_questions[:5]
        return_question = self.regular_questions[7]
        reported_question = self.regular_questions[5]
        return_question_less = self.regular_questions[6]
        zero_questions = self.regular_questions[8:-1]

        seen_question = self.regular_questions[-1]
        AnswerData.objects.create(
            user=self.user,
            question_id=seen_question.question_id,
            category=Question.Category.MATH,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=False,
            followed_plan=True,
            is_correct=True,
            is_final=True,
            is_report=True
        )

        report_user, _ = User.objects.get_or_create(user_id=123456789, name=f"reporter")
        AnswerData.objects.create(
            user=report_user,
            question_id=reported_question.question_id,
            category=Question.Category.MATH,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=False,
            followed_plan=True,
            is_correct=True,
            is_final=True,
            is_report=True
        )

        # set up questions that overflowed
        for question in overflow_questions:
            num_annot = random.randint(3, 10)
            for epoch in range(num_annot):
                curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=question.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

        # questions with 1 to 5 (inclusive) diff users who have looked at it
        for epoch in range(1, 3):
            curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")

            if epoch != 1:
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=return_question_less.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

                AnswerData.objects.create(
                    user=report_user,
                    question_id=reported_question.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

            AnswerData.objects.create(
                    user=curr_user,
                    question_id=return_question.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )
        
    
            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MATH, False
            )
            assert next_question == return_question

        epoch = 3
        curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
        AnswerData.objects.create(
                user=curr_user,
                question_id=return_question.question_id,
                category=Question.Category.MATH,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )
        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MATH, False
        )
        assert next_question == reported_question

    def test_reported_questions_are_seen(self):
        """Ensure reported questions count as being seen by the user"""
        seen_question = self.regular_questions[0]
        reported_question = self.regular_questions[1]
        unseen_question = self.regular_questions[2]

        for flag in [True, False]:
            AnswerData.objects.create(
                user=self.user,
                question_id=seen_question.question_id,
                category=Question.Category.MATH,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=flag,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )

            AnswerData.objects.create(
                user=self.user,
                question_id=reported_question.question_id,
                category=Question.Category.MATH,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=flag,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=True
            )

            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MATH, flag
            )
            assert next_question == unseen_question


@pytest.mark.django_db
class TestDecideNextQuestionTrivia:
    def setup_method(self):
        # Create test data
        self.consumer = QuizbowlConsumer()

        self.room = Room.objects.create()
        self.user = User.objects.create(name="testuser", user_id=1000)
        self.player = Player.objects.create(user=self.user, room=self.room)

        # Create tutorial, sanity, and regular questions
        self.tutorial_question = Question.objects.create(
            question_id=1,
            generation_method=Question.GenerationMethod.TUTORIAL,
            category=Question.Category.MULTIHOP
        )

        self.sanity_question = Question.objects.create(
            question_id=2,
            generation_method=Question.GenerationMethod.ATTENTION_PAIRWISE,
            category=Question.Category.MULTIHOP
        )

        self.sanity_question_swap = Question.objects.create(
            question_id=2000,
            generation_method=Question.GenerationMethod.ATTENTION_SWAP,
            category=Question.Category.MULTIHOP
        )

        self.regular_questions = [
            Question.objects.create(
                question_id=idx,
                generation_method=Question.GenerationMethod.LLAMA,
                category=Question.Category.MULTIHOP
            )
            for idx in range(3, 20)
        ]

        self.extra_questions = [
            Question.objects.create(
                question_id=idx,
                generation_method=Question.GenerationMethod.LLAMA,
                category=Question.Category.MATH
            )
            for idx in range(100, 200)
        ]

        for flag in [True, False]:
            for q in self.extra_questions:
                AnswerData.objects.create(
                    user=self.user,
                    question_id=q.question_id,
                    category=Question.Category.MATH,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=flag,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

    def test_tutorial_question(self):
        """If the user has seen 0 questions, return the tutorial question."""
        with patch.dict("os.environ", {"NUM_SEEN_FOR_TUTORIAL": "0"}):
            for flag in [True, False]:
                next_question = self.consumer.decide_next_question(
                    self.room, self.player, Question.Category.MULTIHOP, flag
                )
                assert next_question == self.tutorial_question

    def test_sanity_question(self):
        """If the user has seen 7 questions, return the sanity question."""

        for question in self.regular_questions[:7]:
            AnswerData.objects.create(
                user=self.user,
                question_id=question.question_id,
                category=Question.Category.MULTIHOP,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )
        AnswerData.objects.create(
            user=self.user,
            question_id=self.tutorial_question.question_id,
            category=Question.Category.MULTIHOP,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=True,
            followed_plan=True,
            is_correct=True,
            is_final=True
        )

        for question in self.regular_questions[-7:]:
            AnswerData.objects.create(
                user=self.user,
                question_id=question.question_id,
                category=Question.Category.MULTIHOP,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )

        AnswerData.objects.create(
            user=self.user,
            question_id=self.tutorial_question.question_id,
            category=Question.Category.MULTIHOP,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=False,
            followed_plan=True,
            is_correct=True,
            is_final=True
        )

        # next_question = self.consumer.decide_next_question(
        #     self.room, self.player, Question.Category.MATH, True
        # )
        # assert next_question == self.sanity_question

        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MULTIHOP, False
        )
        assert next_question == self.sanity_question_swap

    def test_last_unseen_question(self):
        """If the user has seen n - 1 questions, return the last unseen question."""
        for flag in [True, False]:
            for question in self.regular_questions[:-1]:
                AnswerData.objects.create(
                    user=self.user,
                    question_id=question.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=flag,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MULTIHOP, True
        )
        assert next_question == self.regular_questions[-1]

        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MULTIHOP, False
        )
        assert next_question == self.regular_questions[-1]

    def test_unseen_questions_split(self):
        """Ensure we only schedule unseen questions"""
        for flag in [True, False]:
            seen_ids = set()
            for question in self.regular_questions[:7]:
                AnswerData.objects.create(
                    user=self.user,
                    question_id=question.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=flag,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )
                seen_ids.add(question.question_id)

            for _ in range(100):
                next_question = self.consumer.decide_next_question(
                    self.room, self.player, Question.Category.MULTIHOP, flag
                )
                assert next_question.question_id not in seen_ids

    def test_annotation_based_question(self):
        """Return the question with between 1 and 6 annotations over 0 or more than 5 (pairwise setting)."""

        overflow_questions = self.regular_questions[:5]
        return_question = self.regular_questions[7]
        question_seen = self.regular_questions[5]
        return_question_less = self.regular_questions[6]
        zero_questions = self.regular_questions[8:]

        # ======================================== PAIRWISE SETTING TYPE ========================================

        AnswerData.objects.create(
            user=self.user,
            question_id=question_seen.question_id,
            category=Question.Category.MULTIHOP,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=True,
            followed_plan=True,
            is_correct=True,
            is_final=True
        )

        with override_settings(SETTING_TYPE="pairwise"):

            # set up questions that overflowed
            for question in overflow_questions:
                num_annot = random.randint(6, 10)
                for epoch in range(num_annot):
                    curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
                    AnswerData.objects.create(
                        user=curr_user,
                        question_id=question.question_id,
                        category=Question.Category.MULTIHOP,
                        final_instructions_letter="A",
                        instructions_a={},
                        instructions_b={},
                        subanswers_a={},
                        subanswers_b={},
                        steps_seen_a=1,
                        steps_seen_b=1,
                        did_comparison=True,
                        followed_plan=True,
                        is_correct=True,
                        is_final=True
                    )

            # questions with 1 to 5 (inclusive) diff users who have looked at it
            for epoch in range(1, 6):
                curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")

                if epoch != 1:
                    AnswerData.objects.create(
                            user=curr_user,
                            question_id=return_question_less.question_id,
                            category=Question.Category.MULTIHOP,
                            final_instructions_letter="A",
                            instructions_a={},
                            instructions_b={},
                            subanswers_a={},
                            subanswers_b={},
                            steps_seen_a=1,
                            steps_seen_b=1,
                            did_comparison=True,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True
                        )
                AnswerData.objects.create(
                        user=curr_user,
                        question_id=return_question.question_id,
                        category=Question.Category.MULTIHOP,
                        final_instructions_letter="A",
                        instructions_a={},
                        instructions_b={},
                        subanswers_a={},
                        subanswers_b={},
                        steps_seen_a=1,
                        steps_seen_b=1,
                        did_comparison=True,
                        followed_plan=True,
                        is_correct=True,
                        is_final=True
                    )
                AnswerData.objects.create(
                        user=curr_user,
                        question_id=question_seen.question_id,
                        category=Question.Category.MULTIHOP,
                        final_instructions_letter="A",
                        instructions_a={},
                        instructions_b={},
                        subanswers_a={},
                        subanswers_b={},
                        steps_seen_a=1,
                        steps_seen_b=1,
                        did_comparison=True,
                        followed_plan=True,
                        is_correct=True,
                        is_final=True
                    )
        
                next_question = self.consumer.decide_next_question(
                    self.room, self.player, Question.Category.MULTIHOP, True
                )
                assert next_question == return_question

        epoch = 6
        curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
        AnswerData.objects.create(
                user=curr_user,
                question_id=return_question.question_id,
                category=Question.Category.MULTIHOP,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )
        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MULTIHOP, True
        )
        assert next_question == return_question_less

        # ======================================== SWAP SETTING TYPE ========================================

    def test_annotation_based_question_swap(self):
        """Return the question with between 1 and 3 annotations over 0 or more than 3 (swap setting)."""

        overflow_questions = self.regular_questions[:5]
        return_question = self.regular_questions[7]
        question_seen = self.regular_questions[5]
        return_question_less = self.regular_questions[6]
        zero_questions = self.regular_questions[8:]

        AnswerData.objects.create(
            user=self.user,
            question_id=question_seen.question_id,
            category=Question.Category.MULTIHOP,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=False,
            followed_plan=True,
            is_correct=True,
            is_final=True
        )

        # set up questions that overflowed
        for question in overflow_questions:
            num_annot = random.randint(3, 10)
            for epoch in range(num_annot):
                curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=question.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

        # questions with 1 to 5 (inclusive) diff users who have looked at it
        for epoch in range(1, 3):
            curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")

            if epoch != 1:
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=return_question_less.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

            AnswerData.objects.create(
                    user=curr_user,
                    question_id=return_question.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )
            AnswerData.objects.create(
                    user=curr_user,
                    question_id=question_seen.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )
    
            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MULTIHOP, False
            )
            assert next_question == return_question

        epoch = 3
        curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
        AnswerData.objects.create(
                user=curr_user,
                question_id=return_question.question_id,
                category=Question.Category.MULTIHOP,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )
        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MULTIHOP, False
        )
        assert next_question == return_question_less

    def test_seen_all_and_all_annotated(self):

        for question in self.regular_questions:
            for epoch in range(20):
                curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=question.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )
            AnswerData.objects.create(
                user=self.user,
                question_id=question.question_id,
                category=Question.Category.MULTIHOP,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )

        all_questions = set()
        for _ in range(1000):
            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MULTIHOP, False
            )
            all_questions.add(next_question.question_id)

        assert all_questions == set([q.question_id for q in self.regular_questions])

    def test_all_annotated_but_some_unseen(self):

        for question in self.regular_questions:
            for epoch in range(20):
                curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=question.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

        for question in self.regular_questions[:-5]:
            AnswerData.objects.create(
                user=self.user,
                question_id=question.question_id,
                category=Question.Category.MULTIHOP,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )

        all_questions = set()
        for _ in range(1000):
            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MULTIHOP, False
            )
            all_questions.add(next_question.question_id)

        assert all_questions == set([q.question_id for q in self.regular_questions[-5:]])

    def test_report_unannotated_question(self):
        """Ensure reported questions are not counted in the annotation."""

        overflow_questions = self.regular_questions[:5]
        return_question = self.regular_questions[7]
        reported_question = self.regular_questions[5]
        return_question_less = self.regular_questions[6]
        zero_questions = self.regular_questions[8:-1]

        seen_question = self.regular_questions[-1]
        AnswerData.objects.create(
            user=self.user,
            question_id=seen_question.question_id,
            category=Question.Category.MULTIHOP,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=False,
            followed_plan=True,
            is_correct=True,
            is_final=True,
            is_report=True
        )

        report_user, _ = User.objects.get_or_create(user_id=123456789, name=f"reporter")
        AnswerData.objects.create(
            user=report_user,
            question_id=reported_question.question_id,
            category=Question.Category.MULTIHOP,
            final_instructions_letter="A",
            instructions_a={},
            instructions_b={},
            subanswers_a={},
            subanswers_b={},
            steps_seen_a=1,
            steps_seen_b=1,
            did_comparison=False,
            followed_plan=True,
            is_correct=True,
            is_final=True,
            is_report=True
        )

        # set up questions that overflowed
        for question in overflow_questions:
            num_annot = random.randint(3, 10)
            for epoch in range(num_annot):
                curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=question.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

        # questions with 1 to 5 (inclusive) diff users who have looked at it
        for epoch in range(1, 3):
            curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")

            if epoch != 1:
                AnswerData.objects.create(
                    user=curr_user,
                    question_id=return_question_less.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

                AnswerData.objects.create(
                    user=report_user,
                    question_id=reported_question.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )

            AnswerData.objects.create(
                    user=curr_user,
                    question_id=return_question.question_id,
                    category=Question.Category.MULTIHOP,
                    final_instructions_letter="A",
                    instructions_a={},
                    instructions_b={},
                    subanswers_a={},
                    subanswers_b={},
                    steps_seen_a=1,
                    steps_seen_b=1,
                    did_comparison=False,
                    followed_plan=True,
                    is_correct=True,
                    is_final=True
                )
        
    
            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MULTIHOP, False
            )
            assert next_question == return_question

        epoch = 3
        curr_user, _ = User.objects.get_or_create(user_id=epoch, name=f"user{epoch}")
        AnswerData.objects.create(
                user=curr_user,
                question_id=return_question.question_id,
                category=Question.Category.MULTIHOP,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )
        next_question = self.consumer.decide_next_question(
            self.room, self.player, Question.Category.MULTIHOP, False
        )
        assert next_question == reported_question

    def test_reported_questions_are_seen(self):
        """Ensure reported questions count as being seen by the user"""
        seen_question = self.regular_questions[0]
        reported_question = self.regular_questions[1]
        unseen_question = self.regular_questions[2]

        for flag in [True, False]:
            AnswerData.objects.create(
                user=self.user,
                question_id=seen_question.question_id,
                category=Question.Category.MULTIHOP,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=flag,
                followed_plan=True,
                is_correct=True,
                is_final=True
            )

            AnswerData.objects.create(
                user=self.user,
                question_id=reported_question.question_id,
                category=Question.Category.MULTIHOP,
                final_instructions_letter="A",
                instructions_a={},
                instructions_b={},
                subanswers_a={},
                subanswers_b={},
                steps_seen_a=1,
                steps_seen_b=1,
                did_comparison=flag,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=True
            )

            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MULTIHOP, flag
            )
            assert next_question == unseen_question