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
        assert consumer.decide_instruction_to_show(self.room, self.player) == "A"

        # ATTENTION_SWAP
        self.room.current_question.generation_method = Question.GenerationMethod.ATTENTION_SWAP
        assert consumer.decide_instruction_to_show(self.room, self.player) == "A"

    def test_decide_instruction_to_show_swap_distribution(self):
        """Test when SETTING_TYPE is 'swap'."""
        consumer = QuizbowlConsumer()
        self.user.experiment_group = User.ExperimentGroup.SWAP
        self.user.save()
        # Should follow the mocked random.uniform values
        self.room.current_question.generation_method = Question.GenerationMethod.LLAMA
        out = []
        for _ in range(1000):
            out.append(consumer.decide_instruction_to_show(self.room, self.player))
        sum_a = sum([o == 'A' for o in out])
        assert 450 <= sum_a <= 550

    def test_decide_instruction_to_show_pairwise_balancing(self):
        """Test when SETTING_TYPE is 'pairwise'."""
        consumer = QuizbowlConsumer()
        self.user.experiment_group = User.ExperimentGroup.PAIRWISE
        self.user.save()

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
            followed_plan=True,
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
            followed_plan=True,
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
            followed_plan=True,
            is_correct=True,
            is_final=True,
            guessed_answer={"guess": "Guessed answer"},
            true_answer={"true": "True answer"},
            final_instructions_letter="A",
        )
        # Should return "A" because "A" has been seen less
        for _ in range(1000):
            assert consumer.decide_instruction_to_show(self.room, self.player) == "A"

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
            followed_plan=True,
            is_correct=True,
            is_final=True,
            guessed_answer={"guess": "Guessed answer"},
            true_answer={"true": "True answer"},
            final_instructions_letter="A",
        )

        out = []
        for _ in range(1000):
            out.append(consumer.decide_instruction_to_show(self.room, self.player))
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
            followed_plan=True,
            is_correct=True,
            is_final=True,
            guessed_answer={"guess": "Guessed answer"},
            true_answer={"true": "True answer"},
            final_instructions_letter="A",
        )
        for _ in range(50):
            assert consumer.decide_instruction_to_show(self.room, self.player) == "B"

    def test_report(self):

        consumer = QuizbowlConsumer()
        self.user.experiment_group = User.ExperimentGroup.PAIRWISE
        self.user.save()

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
            followed_plan=True,
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
            followed_plan=True,
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
            followed_plan=True,
            is_correct=True,
            is_final=True,
            is_report=True,
            guessed_answer={"guess": "Guessed answer"},
            true_answer={"true": "True answer"},
            final_instructions_letter="A",
        )

        for _ in range(50):
            assert consumer.decide_instruction_to_show(self.room, self.player) == "A"

    def test_rogue_users(self):

        consumer = QuizbowlConsumer()
        self.user.experiment_group = User.ExperimentGroup.PAIRWISE
        self.user.save()

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
            followed_plan=True,
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
            is_report=False,
            guessed_answer={"guess": "Guessed answer"},
            true_answer={"true": "True answer"},
            final_instructions_letter="B",
        )

        for _ in range(50):
            assert consumer.decide_instruction_to_show(self.room, self.player) == "B"

@pytest.mark.django_db
class TestExperimentGroup:

    def setup_method(self):

        self.trivia_questions = [
            Question.objects.create(
                question_id=idx,
                generation_method=Question.GenerationMethod.QWEN,
                category=Question.Category.MULTIHOP
            )
            for idx in range(0, 5)
        ]

        self.math_questions = [
            Question.objects.create(
                question_id=idx,
                generation_method=Question.GenerationMethod.QWEN,
                category=Question.Category.MATH
            )
            for idx in range(5, 11)
        ]

        self.consumer = QuizbowlConsumer()


    def test_user_exists(self):
        user = User.objects.create(name="testuser", user_id=1000, experiment_group=User.ExperimentGroup.PAIRWISE)
        assert self.consumer.decide_expt_group(user) == User.ExperimentGroup.PAIRWISE

        user.experiment_group = User.ExperimentGroup.SWAP
        user.save()
        assert self.consumer.decide_expt_group(user) == User.ExperimentGroup.SWAP

    def test_rogue_and_report_dont_count(self):

        user = User.objects.create(name="testuser", user_id=1000)

        for user_num in range(6):
            pairwise_user, _ = User.objects.get_or_create(name="pairwise_" + str(user_num), user_id=user_num, experiment_group=User.ExperimentGroup.PAIRWISE)

            AnswerData.objects.create(
                question_id=self.math_questions[0].question_id,
                user=pairwise_user,
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

        for _ in range(2):
            for user_num in range(12):
                swap_user, _ = User.objects.get_or_create(name="swap_" + str(user_num), user_id=user_num + 200, experiment_group=User.ExperimentGroup.PAIRWISE)

                if user_num < 6:
                    AnswerData.objects.create(
                        question_id=self.math_questions[1].question_id,
                        user=swap_user,
                        category=Question.Category.MULTIHOP,
                        instructions_a={"step1": "Do this"},
                        instructions_b={"step1": "Do that"},
                        subanswers_a={"sub1": "Answer A1"},
                        subanswers_b={"sub1": "Answer B1"},
                        steps_seen_a=3,
                        steps_seen_b=2,
                        did_comparison=False,
                        followed_plan=True,
                        is_correct=True,
                        is_final=True,
                        is_report=True,
                        guessed_answer={"guess": "Guessed answer"},
                        true_answer={"true": "True answer"},
                        final_instructions_letter="A",
                    )
                else:
                    AnswerData.objects.create(
                        question_id=self.math_questions[1].question_id,
                        user=swap_user,
                        category=Question.Category.MULTIHOP,
                        instructions_a={"step1": "Do this"},
                        instructions_b={"step1": "Do that"},
                        subanswers_a={"sub1": "Answer A1"},
                        subanswers_b={"sub1": "Answer B1"},
                        steps_seen_a=3,
                        steps_seen_b=2,
                        did_comparison=False,
                        followed_plan=False,
                        is_correct=True,
                        is_final=True,
                        is_report=False,
                        guessed_answer={"guess": "Guessed answer"},
                        true_answer={"true": "True answer"},
                        final_instructions_letter="A",
                    )

        assert self.consumer.decide_expt_group(user) == User.ExperimentGroup.SWAP

    def test_rogue_and_report_dont_count_flipped(self):

        user = User.objects.create(name="testuser", user_id=1000)

        for user_num in range(6):
            swap_user, _ = User.objects.get_or_create(name="swap_" + str(user_num), user_id=user_num + 200, experiment_group=User.ExperimentGroup.PAIRWISE)

            AnswerData.objects.create(
                question_id=self.math_questions[0].question_id,
                user=swap_user,
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

        for _ in range(2):
            for user_num in range(12):
                pairwise_user, _ = User.objects.get_or_create(name="pairwise_" + str(user_num), user_id=user_num, experiment_group=User.ExperimentGroup.PAIRWISE)

                if user_num < 6:
                    AnswerData.objects.create(
                        question_id=self.math_questions[1].question_id,
                        user=pairwise_user,
                        category=Question.Category.MULTIHOP,
                        instructions_a={"step1": "Do this"},
                        instructions_b={"step1": "Do that"},
                        subanswers_a={"sub1": "Answer A1"},
                        subanswers_b={"sub1": "Answer B1"},
                        steps_seen_a=3,
                        steps_seen_b=2,
                        did_comparison=False,
                        followed_plan=True,
                        is_correct=True,
                        is_final=True,
                        is_report=True,
                        guessed_answer={"guess": "Guessed answer"},
                        true_answer={"true": "True answer"},
                        final_instructions_letter="A",
                    )
                else:
                    AnswerData.objects.create(
                        question_id=self.math_questions[1].question_id,
                        user=pairwise_user,
                        category=Question.Category.MULTIHOP,
                        instructions_a={"step1": "Do this"},
                        instructions_b={"step1": "Do that"},
                        subanswers_a={"sub1": "Answer A1"},
                        subanswers_b={"sub1": "Answer B1"},
                        steps_seen_a=3,
                        steps_seen_b=2,
                        did_comparison=False,
                        followed_plan=False,
                        is_correct=True,
                        is_final=True,
                        is_report=False,
                        guessed_answer={"guess": "Guessed answer"},
                        true_answer={"true": "True answer"},
                        final_instructions_letter="A",
                    )

        assert self.consumer.decide_expt_group(user) == User.ExperimentGroup.PAIRWISE
        

    def test_more_swap_questions_done(self):

        user = User.objects.create(name="testuser", user_id=1000)

        for num_swap_done in range(5):

            if num_swap_done != 0:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(random.randint(6, 9)):
                        pairwise_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_pairwise_" + str(user_num), user_id=int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.PAIRWISE)

                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=pairwise_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=True,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )

            if True:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(random.randint(3, 7)):
                        swap_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_swap_" + str(user_num), user_id=10000+int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.SWAP)
                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=swap_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=False,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )

            assert self.consumer.decide_expt_group(user) == User.ExperimentGroup.PAIRWISE

    def test_more_swap_questions_done(self):

        user = User.objects.create(name="testuser", user_id=1000)

        for num_swap_done in range(5):

            if True:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(random.randint(6, 9)):
                        pairwise_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_pairwise_" + str(user_num), user_id=int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.PAIRWISE)

                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=pairwise_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=True,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )

            if num_swap_done != 0:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(random.randint(3, 7)):
                        swap_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_swap_" + str(user_num), user_id=10000+int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.SWAP)
                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=swap_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=False,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )

            assert self.consumer.decide_expt_group(user) == User.ExperimentGroup.SWAP

    def test_equal_questions_done_and_more_swap_users(self):

        user = User.objects.create(name="testuser", user_id=1000)
        
        # extra swap user
        User.objects.create(name="randuser", user_id=2134561923, experiment_group = User.ExperimentGroup.SWAP)

        for num_swap_done in range(5):

            assert self.consumer.decide_expt_group(user) == User.ExperimentGroup.PAIRWISE

            if True:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(6):
                        pairwise_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_pairwise_" + str(user_num), user_id=int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.PAIRWISE)

                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=pairwise_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=True,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )

            if True:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(6):
                        swap_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_swap_" + str(user_num), user_id=10000+int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.SWAP)
                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=swap_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=False,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )


    def test_equal_questions_done_and_more_pairwise_users(self):

        user = User.objects.create(name="testuser", user_id=1000)
        
        # extra swap user
        User.objects.create(name="randuser", user_id=2134561923, experiment_group = User.ExperimentGroup.PAIRWISE)

        for num_swap_done in range(5):

            assert self.consumer.decide_expt_group(user) == User.ExperimentGroup.SWAP

            if True:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(6):
                        pairwise_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_pairwise_" + str(user_num), user_id=int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.PAIRWISE)

                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=pairwise_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=True,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )

            if True:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(6):
                        swap_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_swap_" + str(user_num), user_id=10000+int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.SWAP)
                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=swap_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=False,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )


    def test_equal_questions_done_and_equal_users(self):

        user = User.objects.create(name="testuser", user_id=1000)

        for num_swap_done in range(5):

            out = []
            for _ in range(100):
                out.append(self.consumer.decide_expt_group(user))
            num_swap = [o == User.ExperimentGroup.SWAP for o in out]
            assert 35 <= sum(num_swap) <= 65

            if True:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(6):
                        pairwise_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_pairwise_" + str(user_num), user_id=int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.PAIRWISE)

                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=pairwise_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=True,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )

            if True:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(6):
                        swap_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_swap_" + str(user_num), user_id=10000+int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.SWAP)
                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=swap_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=False,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )

    def test_all_questions_done(self):

        user = User.objects.create(name="testuser", user_id=1000)

        for num_swap_done in range(5):

            if True:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(6):
                        pairwise_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_pairwise_" + str(user_num), user_id=int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.PAIRWISE)

                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=pairwise_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=True,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )

            if True:
                for qs, c in [(self.math_questions, Question.Category.MATH), (self.trivia_questions, Question.Category.MULTIHOP)]:

                    for user_num in range(6):
                        swap_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_swap_" + str(user_num), user_id=10000+int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.SWAP)
                        AnswerData.objects.create(
                            question_id=qs[num_swap_done].question_id,
                            user=swap_user,
                            category=c,
                            instructions_a={"step1": "Do this"},
                            instructions_b={"step1": "Do that"},
                            subanswers_a={"sub1": "Answer A1"},
                            subanswers_b={"sub1": "Answer B1"},
                            steps_seen_a=3,
                            steps_seen_b=2,
                            did_comparison=False,
                            followed_plan=True,
                            is_correct=True,
                            is_final=True,
                            is_report=False,
                            guessed_answer={"guess": "Guessed answer"},
                            true_answer={"true": "True answer"},
                            final_instructions_letter="A",
                        )

        for user_num in range(6):
            swap_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_swap_" + str(user_num), user_id=10000+int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.SWAP)
            pairwise_user, _ = User.objects.get_or_create(name=str(num_swap_done) + "_swap_" + str(user_num), user_id=10000+int(str(num_swap_done) + str(user_num)), experiment_group=User.ExperimentGroup.SWAP)
            AnswerData.objects.create(
                question_id=self.math_questions[-1].question_id,
                user=swap_user,
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )
            AnswerData.objects.create(
                question_id=self.math_questions[-1].question_id,
                user=pairwise_user,
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )      
        
        out = []
        for _ in range(100):
            out.append(self.consumer.decide_expt_group(user))
        num_swap = [o == User.ExperimentGroup.SWAP for o in out]
        assert 35 <= sum(num_swap) <= 65
        

@pytest.mark.django_db
class TestEverythingQuestions:

    def setup_method(self):

        self.trivia_questions = [
            Question.objects.create(
                question_id=idx,
                generation_method=Question.GenerationMethod.QWEN,
                category=Question.Category.MULTIHOP
            )
            for idx in range(0, 10)
        ]

        self.math_questions = [
            Question.objects.create(
                question_id=idx,
                generation_method=Question.GenerationMethod.QWEN,
                category=Question.Category.MATH
            )
            for idx in range(10, 20)
        ]

        self.room = Room.objects.create(
            current_question=self.trivia_questions[0]
        )

        self.user = User.objects.create(name="testuser", user_id=1000)
        self.player = Player.objects.create(user=self.user, room=self.room)

    def test_report_does_nothing(self):

        for q in self.trivia_questions:
            AnswerData.objects.create(
                question_id=q.question_id,
                user=self.user,
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=False,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=True,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )
        consumer = QuizbowlConsumer()
        for _ in range(10):
            assert consumer.decide_question_category(self.player) == Question.Category.MATH

    def test_rogue_does_nothing(self):

        for q in self.math_questions:
            AnswerData.objects.create(
                question_id=q.question_id,
                user=self.user,
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
                final_instructions_letter="A",
            )
        consumer = QuizbowlConsumer()
        for _ in range(10):
            assert consumer.decide_question_category(self.player) == Question.Category.MULTIHOP
        

    def test_all_math_seen(self):

        for question in self.math_questions:
            AnswerData.objects.create(
                question_id=question.question_id,
                user=self.user,
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

        consumer = QuizbowlConsumer()
        assert consumer.decide_question_category(self.player) == Question.Category.MULTIHOP

    def test_all_trivia_seen(self):

        for question in self.trivia_questions:
            AnswerData.objects.create(
                question_id=question.question_id,
                user=self.user,
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

        consumer = QuizbowlConsumer()
        assert consumer.decide_question_category(self.player) == Question.Category.MATH

    def test_all_seen(self):

        for question in self.trivia_questions:
            AnswerData.objects.create(
                question_id=question.question_id,
                user=self.user,
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

        for question in self.math_questions:
            AnswerData.objects.create(
                question_id=question.question_id,
                user=self.user,
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

        consumer = QuizbowlConsumer()
        out = []
        for _ in range(1000):
            out.append(consumer.decide_question_category(self.player))
        sum_a = sum([o == Question.Category.MATH for o in out])
        assert 450 <= sum_a <= 550

    def test_not_all_seen(self):

        for question in self.trivia_questions[:-1]:
            AnswerData.objects.create(
                question_id=question.question_id,
                user=self.user,
                category=Question.Category.MULTIHOP,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

        for question in self.math_questions[:-1]:
            AnswerData.objects.create(
                question_id=question.question_id,
                user=self.user,
                category=Question.Category.MATH,
                instructions_a={"step1": "Do this"},
                instructions_b={"step1": "Do that"},
                subanswers_a={"sub1": "Answer A1"},
                subanswers_b={"sub1": "Answer B1"},
                steps_seen_a=3,
                steps_seen_b=2,
                did_comparison=True,
                followed_plan=True,
                is_correct=True,
                is_final=True,
                is_report=False,
                guessed_answer={"guess": "Guessed answer"},
                true_answer={"true": "True answer"},
                final_instructions_letter="A",
            )

        consumer = QuizbowlConsumer()
        out = []
        for _ in range(1000):
            out.append(consumer.decide_question_category(self.player))
        sum_a = sum([o == Question.Category.MATH for o in out])
        assert 450 <= sum_a <= 550
    

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
        assert consumer.decide_instruction_to_show(self.room, self.player) == "A"

        # ATTENTION_SWAP
        self.room.current_question.generation_method = Question.GenerationMethod.ATTENTION_SWAP
        assert consumer.decide_instruction_to_show(self.room, self.player) == "A"

    def test_decide_instruction_to_show_swap_distribution(self):
        """Test when SETTING_TYPE is 'swap'."""
        consumer = QuizbowlConsumer()
        with patch.dict("os.environ", {"SETTING_TYPE": "swap"}):
            # Should follow the mocked random.uniform values
            self.room.current_question.generation_method = Question.GenerationMethod.LLAMA
            out = []
            for _ in range(1000):
                out.append(consumer.decide_instruction_to_show(self.room, self.player))
            sum_a = sum([o == 'A' for o in out])
            assert 450 <= sum_a <= 550

    def test_decide_instruction_to_show_pairwise_balancing(self):
        """Test when SETTING_TYPE is 'pairwise'."""
        consumer = QuizbowlConsumer()
        self.user.experiment_group = User.ExperimentGroup.PAIRWISE
        self.user.save()

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
            followed_plan=True,
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
            followed_plan=True,
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
            followed_plan=True,
            is_correct=True,
            is_final=True,
            guessed_answer={"guess": "Guessed answer"},
            true_answer={"true": "True answer"},
            final_instructions_letter="A",
        )
        # Should return "A" because "A" has been seen less
        for _ in range(1000):
            assert consumer.decide_instruction_to_show(self.room, self.player) == "A"

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
            followed_plan=True,
            is_correct=True,
            is_final=True,
            guessed_answer={"guess": "Guessed answer"},
            true_answer={"true": "True answer"},
            final_instructions_letter="A",
        )

        out = []
        for _ in range(1000):
            out.append(consumer.decide_instruction_to_show(self.room, self.player))
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
            followed_plan=True,
            is_correct=True,
            is_final=True,
            guessed_answer={"guess": "Guessed answer"},
            true_answer={"true": "True answer"},
            final_instructions_letter="A",
        )
        for _ in range(50):
            assert consumer.decide_instruction_to_show(self.room, self.player) == "B"

    def test_report(self):

        consumer = QuizbowlConsumer()
        self.user.experiment_group = User.ExperimentGroup.PAIRWISE
        self.user.save()

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
            followed_plan=True,
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
            followed_plan=True,
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
            followed_plan=True,
            is_correct=True,
            is_final=True,
            is_report=True,
            guessed_answer={"guess": "Guessed answer"},
            true_answer={"true": "True answer"},
            final_instructions_letter="B",
        )

        for _ in range(50):
            assert consumer.decide_instruction_to_show(self.room, self.player) == "B"

    def test_rogue_users(self):

        consumer = QuizbowlConsumer()
        self.user.experiment_group = User.ExperimentGroup.PAIRWISE
        self.user.save()

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
            followed_plan=True,
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
            is_report=False,
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
            is_report=False,
            guessed_answer={"guess": "Guessed answer"},
            true_answer={"true": "True answer"},
            final_instructions_letter="B",
        )

        for _ in range(50):
            assert consumer.decide_instruction_to_show(self.room, self.player) == "B"

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
            is_report=False
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

    def test_rogue_unannotated_question(self):
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
            is_report=False
        )

        rogue_user, _ = User.objects.get_or_create(user_id=123456789, name=f"rogue")
        AnswerData.objects.create(
            user=rogue_user,
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
            followed_plan=False,
            is_correct=True,
            is_final=True,
            is_report=False
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
                    user=rogue_user,
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

    def test_rogue_questions_are_seen(self):
        """Ensure rogue questions count as being seen by the user"""
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
                followed_plan=False,
                is_correct=True,
                is_final=True,
                is_report=False
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
            is_report=False
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

    def test_rogue_unannotated_question(self):
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
            is_report=False
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
            followed_plan=False,
            is_correct=True,
            is_final=True,
            is_report=False
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

    def test_rogue_questions_are_seen(self):
        """Ensure rogue questions count as being seen by the user"""
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
                followed_plan=False,
                is_correct=True,
                is_final=True,
                is_report=False
            )

            next_question = self.consumer.decide_next_question(
                self.room, self.player, Question.Category.MULTIHOP, flag
            )
            assert next_question == unseen_question