from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime

import nltk
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
    difficulty = models.TextField(default=Difficulty.HS)
    subdifficulty = models.TextField(default=Subdifficulty.REGULAR)
    generation_method = models.CharField(default=GenerationMethod.HUMAN, choices=GenerationMethod.choices, max_length=30)
    clue_list = models.JSONField(null=True, blank=True)
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

    def get_players(self):

        valid_players = self.players.filter(
            Q(last_seen__gte=datetime.datetime.now().timestamp() - 3600) &
            Q(banned=False)
        )

        player_list = [{
            'user_name': player.user.name,
            'player_id': player.player_id,
            'score': player.score,
            'correct': player.correct,
            'negs': player.negs,
            'last_seen': player.last_seen,
            'active': datetime.datetime.now().timestamp() - player.last_seen < 10,
        } for player in valid_players]

        player_list.sort(key=lambda player: player['score'])
        return player_list

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

    # Generation Method
    guessed_generation_method = models.CharField(choices=Question.GenerationMethod.choices, max_length=30)

    # Interestingness
    interestingness_rating = models.IntegerField(choices=Rating.choices)

    # Pyramidality

    # The clues' text sorted by what the subject thinks is pyramidal (hardest to most easy)
    # For example, ["clue #1 text", "clue #0 text", "clue #2 text", "clue #3 text"], means
    # the 1st clue was easier than the 0th
    submitted_clue_list = models.JSONField(null=True, blank=True)

    # Each original clue index in pyramidal order (hardest to most easy) with clue indices being 0 to n-1
    # For example, [1, 0, 2, 3], means the 1st clue was easier than the 0th
    submitted_clue_order = models.JSONField(null=True, blank=True)

    # For each index i, the value of the below list is true if it is flagged to have content to be not factual
    submitted_untrue_mask_list = models.JSONField(null=True, blank=True) 
    inversions = models.IntegerField()

    feedback_text = models.TextField(blank=True, max_length=500)
    improved_question = models.TextField(blank=False, max_length=500)

    # Book-keeping
    answered_correctly = models.BooleanField()
    buzz_position_word = models.IntegerField(validators=[MinValueValidator(0)])
    buzz_position_norm = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    buzzed = models.BooleanField(default=False)
    submission_datetime = models.DateTimeField(null=True)

    def __str__(self):
        return f"Feedback for Question {self.question.question_id} by {self.player.user.name} ({self.player.user.user_id})"
    
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
        return self.player.user.name + "(" + self.tag + ")" ":" + self.content