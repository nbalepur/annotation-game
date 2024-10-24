from django.contrib import admin
from django.utils.html import format_html
from .models import *
from .resource import *
from import_export.admin import ExportActionMixin, ImportExportModelAdmin
from django.http import HttpResponse
import csv

class ExportAdminMixin(ExportActionMixin):
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(self.model._meta.verbose_name_plural.lower())
        
        writer = csv.writer(response)
        field_names = [field.name for field in self.model._meta.fields]
        writer.writerow([field.replace('_', ' ').title() for field in field_names])

        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected Objects as CSV"

def unban_players(modeladmin, request, queryset):
    for player in queryset:
        player.unban()
        player.save()
        
unban_players.short_description = "Unban players"

@admin.register(Question)
class QuestionAdmin(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['question_id', 'category', 'content', 'answer', 'difficulty', 'subdifficulty', 'is_human_written', 'generation_method']
    actions = ['export_as_csv', unban_players]
    search_fields = ['question_id', 'content', 'answer']
    resource_class = QuestionResource

@admin.register(Room)
class RoomAdmin(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['label', 'collects_feedback', 'max_players', 'state', 'current_question', 'start_time', 'end_time', 'buzz_player', 'buzz_start_time', 'buzz_end_time', 'category', 'difficulty', 'change_locked', 'speed']
    actions = ['export_as_csv', unban_players]
    resource_class = RoomResource

@admin.register(User)
class UserAdmin(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['user_id', 'name']
    actions = ['export_as_csv', unban_players]
    resource_class = UserResource

@admin.register(Player)
class PlayerAdmin(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['player_id', 'user', 'room', 'score', 'correct', 'negs', 'locked_out', 'banned', 'last_seen']
    actions = ['export_as_csv', unban_players]
    resource_class = PlayerResource

@admin.register(QuestionFeedback)
class QuestionFeedbackAdmin(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['question', 'player', 'guessed_answer', 'guessed_generation_method', 'interestingness_rating', 'submitted_clue_order', 'submitted_factual_mask_list', 'inversions', 'feedback_text', 'answered_correctly', 'buzz_position_word', 'buzz_position_norm', 'buzzed', 'skipped', 'solicit_additional_feedback', 'guessed_gen_method_correctly', 'initial_submission_datetime', 'additional_submission_datetime', 'is_submitted']
    actions = ['export_as_csv', unban_players]
    resource_class = QuestionFeedbackResource

@admin.register(Message)
class MessageAdmin(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['message_id', 'room', 'player', 'content', 'tag', 'timestamp', 'visible']
    actions = ['export_as_csv', unban_players]
    resource_class = MessageResource

@admin.register(ToolLog)
class ToolLog(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['tool_log_id', 'question_id', 'user_id', 'instruction_type', 'tool_name', 'tool_query', 'tool_result', 'tool_execution_status', 'queried_at']
    actions = ['export_as_csv']
    resource_class = MessageResource

@admin.register(Document)
class Document(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['document_id', 'doc_id', 'document_text']
    actions = ['export_as_csv']
    resource_class = MessageResource

@admin.register(ComparisonFeedback)
class ComparisonFeedback(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['question', 'user', 'chosen', 'chosen_adjusted', 'chosen_instruction', 'shown_first']
    actions = ['export_as_csv']
    resource_class = MessageResource

@admin.register(LeaderboardLog)
class LeaderboardLog(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['log_id', 'user', 'question_id', 'correctness_score', 'seconds_taken']
    actions = ['export_as_csv']
    resource_class = MessageResource

@admin.register(ReportIssue)
class ReportIssue(ImportExportModelAdmin, ExportActionMixin):
    list_display = ['report_id', 'user', 'question_id', 'is_bad_question', 'is_bad_instruction', 'is_bad_answer_verifier', 'feedback']
    actions = ['export_as_csv']
    resource_class = MessageResource