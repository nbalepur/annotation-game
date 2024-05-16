from datetime import timedelta
from typing import List
from django.db import models
from django.db.models import Q, Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

import nltk
from math import ceil

from .badges import BuzzBadge, BuzzBadgeStatus

# Download the punkt tokenizer models if not already downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Create your models here.

class Question(models.Model):
    """Quizbowl current_question"""

    class Category(models.TextChoices):
        EVERYTHING = 'Everything', _('Everything')
        SCIENCE = 'Science', _('Science')
        HISTORY = 'History', _('History')
        LITERATURE = 'Literature', _('Literature')
        PHILOSOPHY = 'Philosophy', _('Philosophy')
        RELIGION = 'Religion', _('Religion')
        GEOGRAPHY = 'Geography', _('Geography')
        FINE_ARTS = 'Fine Arts', _('Fine Arts')
        SOCIAL_SCIENCE = 'Social Science', _('Social Science')
        MYTHOLOGY = 'Mythology', _('Mythology')
        TRASH = 'Trash', _('Trash')

    class Difficulty(models.TextChoices):
        COLLEGE = "College", _("College")
        MS = "MS", _("MS")
        HS = "HS", _("HS")
        OPEN = "Open", _("Open")

    class Subdifficulty(models.TextChoices):
        EASY = "easy", _("Easy")
        REGULAR = "regular", _("Regular")
        HARD = "hard", _("Hard")
        NATIONAL = "national", _("National")

    class GenerationMethod(models.TextChoices):
        HUMAN = "human", _("Human-written")
        AI = "ai", _("AI-generated")

    question_id = models.AutoField(primary_key=True)
    group_id = models.IntegerField()
    category = models.TextField(default=Category.EVERYTHING)
    content = models.TextField()

    answer = models.TextField()
    answer_accept = models.JSONField(null=True, blank=True)
    answer_reject = models.JSONField(null=True, blank=True)
    answer_regular_prompt = models.JSONField(null=True, blank=True)
    answer_antiprompt = models.JSONField(null=True, blank=True)
    page_cleaned = models.TextField(default="")

    difficulty = models.TextField(default=Difficulty.HS)
    subdifficulty = models.TextField(default=Subdifficulty.REGULAR)
    is_human_written = models.BooleanField()
    generation_method = models.CharField(default=GenerationMethod.HUMAN, max_length=30)
    clue_list = models.JSONField(null=True, blank=True)
    wiki_sents = models.JSONField(null=True, blank=True)
    length = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    def save(self, *args, **kwargs):
        # Tokenize content into sentences and save to content_sentences
        if self.content and not (self.clue_list or len(self.clue_list) ):
            sentences = nltk.sent_tokenize(self.content)
            self.clue_list = sentences
            self.length = len(sentences)
        super().save(*args, **kwargs)

class Room(models.Model):
    """Room to play quizbowl"""

    class GameState(models.TextChoices):
        IDLE = 'idle', _('Idle')
        PLAYING = 'playing', _('Playing')
        CONTEST = 'contest', _('Contest')

    label = models.SlugField(unique=True)
    collects_feedback = models.BooleanField(default=False)
    max_players = models.IntegerField(default=20, validators=[MinValueValidator(0)])
    state = models.CharField(max_length=9, choices=GameState.choices, default=GameState.IDLE)

    current_question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        related_name='rooms',
        null=True,
        blank=True,
    )
    start_time = models.FloatField(default=0)
    end_time = models.FloatField(default=1)

    buzz_player = models.OneToOneField(
        'Player',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='buzz_player',
    )
    buzz_start_time = models.FloatField(default=0)
    buzz_end_time = models.FloatField(default=1)

    category = models.CharField(
        max_length=30,
        choices=Question.Category.choices,
        default=Question.Category.EVERYTHING,
    )
    difficulty = models.CharField(
        max_length=10,
        choices=Question.Difficulty.choices,
        default=Question.Difficulty.HS,
    )
    change_locked = models.BooleanField(default=False) # Category and difficulty changes locked

    MIN_SPEED, MAX_SPEED, DEFAULT_SPEED = 60, 600, 200
    speed = models.IntegerField(validators=[MinValueValidator(MIN_SPEED), MaxValueValidator(MAX_SPEED)], default=DEFAULT_SPEED) # Reading speed wpm

    def __str__(self):
        return self.label
    
    def get_valid_players(self):
        return self.players.filter(
                    Q(last_seen__gte=timezone.now().timestamp() - 3600) &
                    Q(banned=False)
                )

    def get_players_by_score(self):
        valid_players = self.get_valid_players()

        player_list = [{
            'user_name': player.user.name,
            'player_id': player.player_id,
            'score': player.score,
            'correct': player.correct,
            'negs': player.negs,
            'last_seen': player.last_seen,
            'active': timezone.now().timestamp() - player.last_seen < 10,
        } for player in valid_players]

        player_list.sort(key=lambda player: player['score'])
        return player_list
    
    def get_buzz_badges(self) -> List[BuzzBadge]:
        """
        Method to get the question feedbacks from players in the room.
        """
        players_in_room = self.get_valid_players()

        # Initialize an empty list to store question feedbacks
        buzz_badges: List[BuzzBadge] = []

        # Iterate over each player
        for player in players_in_room:
            # Get the feedbacks given by the player for the current question
            player_feedback: QuestionFeedback = player.feedback.filter(
                    Q(buzz_datetime__gte=timezone.now() - timedelta(seconds=600)) &
                    Q(question=self.current_question) &
                    Q(buzzed=True)
                ).order_by('-buzz_datetime').first()
            
            if (player_feedback is None and player != self.buzz_player): continue

            # Extend the list of question feedbacks with player's feedbacks
            status = None
            index: int = 10**5

            if self.state == Room.GameState.CONTEST and player == self.buzz_player:
                status = BuzzBadgeStatus.CURRENT
            elif player_feedback:
                if player_feedback.answered_correctly:
                    status = BuzzBadgeStatus.CORRECT
                    index = player_feedback.buzz_position_word
                elif not player_feedback.answered_correctly: status = BuzzBadgeStatus.INCORRECT
            else: pass

            buzzBadge = BuzzBadge(index=index, status=status)
            buzz_badges.append(buzzBadge)

        return sorted(buzz_badges, key=lambda b: -b.index)
    
    def compute_words_to_show(self) -> int:
        """Computes the number of words to show based on the elapsed time in the game."""
        current_time = timezone.now().timestamp()
        time_per_chunk = (60 / self.speed)

        if self.state == Room.GameState.IDLE:
            return len(self.current_question.content.split())
        elif self.state == Room.GameState.PLAYING:
            time_elapsed = current_time - self.start_time
        else:
            time_elapsed = self.buzz_start_time - self.start_time

        words_to_show = ceil(time_elapsed / time_per_chunk)
        return min(words_to_show, len(self.current_question.content.split()))

    def get_shown_question(self):
        """Computes the correct amount of the question to show, depending on the state of the game.
            Note, this value is not persisted because, updating is too expensive."""
        word_list: List[str] = ""

        if self.current_question and self.current_question.content:
            full_question = self.current_question.content

            words_to_show = self.compute_words_to_show()
            word_list = full_question.split()[:words_to_show] if (words_to_show > 0) else full_question.split()
        
        buzz_badges = self.get_buzz_badges()

        for bb in buzz_badges:
            word_list.insert(bb.index, str(bb.status))

        return " ".join(word_list)

    def get_messages(self):

        valid_messages = self.messages.filter(visible=True)

        chrono_messages = [{
            'message_id': m.message_id,
            'tag': m.tag,
            'user_name': m.player.user.name,
            'content': m.content
        } for m in valid_messages.order_by('timestamp').reverse()[:50]]

        return chrono_messages

class User(models.Model):
    """Site user"""

    user_id = models.CharField(max_length=100)
    name = models.CharField(max_length=20)
    email = models.CharField(default="", blank=True, max_length=320)

    def __str__(self):
        return str(self.name)


class Player(models.Model):
    """Player (user) in a room"""

    player_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='players',
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='players',
    )
    score = models.IntegerField(default=0)
    correct = models.IntegerField(default=0)
    negs = models.IntegerField(default=0)
    locked_out = models.BooleanField(default=False)
    banned = models.BooleanField(default=False)
    reported_by = models.ManyToManyField('Player')
    last_seen = models.FloatField(default=0)

    def unban(self):
        """Unban player
        """
        self.banned = False
        self.reported_by.clear()
        self.save()

    def __str__(self):
        return self.user.name + ":" + self.room.label

class QuestionFeedback(models.Model):
    """Feedback for quizbowl questions"""

    class Rating(models.IntegerChoices):
        ONE_STAR = 1, _('1 Star')
        TWO_STARS = 2, _('2 Stars')
        THREE_STARS = 3, _('3 Stars')
        FOUR_STARS = 4, _('4 Stars')
        FIVE_STARS = 5, _('5 Stars')

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='feedback',
    )

    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='feedback',
    )

    guessed_answer = models.CharField(default="", max_length=30)

    # Generation Method
    guessed_generation_method = models.CharField(choices=Question.GenerationMethod.choices, max_length=30)

    # Interestingness
    interestingness_rating = models.IntegerField(default=Rating.ONE_STAR, choices=Rating.choices)

    # Pyramidality

    # The clues' text sorted by what the subject thinks is pyramidal (hardest to most easy)
    # For example, ["clue #1 text", "clue #0 text", "clue #2 text", "clue #3 text"], means
    # the 1st clue was easier than the 0th
    submitted_clue_list = models.JSONField(null=True, blank=True)

    # Each original clue index in pyramidal order (hardest to most easy) with clue indices being 0 to n-1
    # For example, [1, 0, 2, 3], means the 1st clue was easier than the 0th
    submitted_clue_order = models.JSONField(null=True, blank=True)

    # For each index i, the value of the below list is true if it is a factual clue
    submitted_factual_mask_list = models.JSONField(null=True, blank=True) 
    inversions = models.IntegerField(default=0)

    feedback_text = models.TextField(blank=True, max_length=500)
    improved_question = models.TextField(blank=False, max_length=500)

    # Play data
    answered_correctly = models.BooleanField()
    buzzed = models.BooleanField(default=False)
    buzz_position_word = models.IntegerField(validators=[MinValueValidator(0)])
    buzz_position_norm = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    buzz_datetime = models.DateTimeField(null=True)

    # Feedback
    solicit_additional_feedback = models.BooleanField(default=False)
    guessed_gen_method_correctly = models.BooleanField(null=True)
    initial_submission_datetime = models.DateTimeField(null=True)
    additional_submission_datetime = models.DateTimeField(null=True)
    is_submitted = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback for Question {self.question.question_id} by {self.player.user.name} ({self.player.user.user_id})"
    
    def is_completed(self) -> bool:
        return ((self.additional_submission_datetime != None and self.solicit_additional_feedback)
                or
                (self.initial_submission_datetime != None and self.is_submitted and not self.solicit_additional_feedback))

    class Meta:
        # Indicate a composite key for player and question
        unique_together = (('question', 'player'),)

class Message(models.Model):
    """Message that can be sent by Players"""

    class MessageTag(models.TextChoices):
        JOIN = 'join', _('Join')
        LEAVE = 'leave', _('Leave')
        BUZZ_INIT = 'buzz_init', _('Buzz Initiated')
        BUZZ_CORRECT = 'buzz_correct', _('Buzz Correct')
        BUZZ_WRONG = 'buzz_wrong', _('Buzz Wrong')
        BUZZ_FORFEIT = 'buzz_forfeit', _('Buzz Forfeit')
        SET_CATEGORY = 'set_category', _('Set Category')
        SET_DIFFICULTY = 'set_difficulty', _('Set Difficulty')
        RESET_SCORE = 'reset_score', _('Reset Score')
        CHAT = 'chat', _('Chat')

    message_id = models.AutoField(primary_key=True)
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    content = models.CharField(max_length=200, null=True, blank=True)
    tag = models.CharField(max_length=20, choices=MessageTag.choices)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    visible = models.BooleanField(default=True)

    def __str__(self):
        return self.player.user.name + "(" + self.tag + ")"
