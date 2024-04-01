from import_export import resources 
from .models import *

class QuestionResource(resources.ModelResource):
     class Meta:
         model = Question

class RoomResource(resources.ModelResource):
     class Meta:
         model = Room
         
class UserResource(resources.ModelResource):
     class Meta:
         model = User

class PlayerResource(resources.ModelResource):
     class Meta:
         model = Player

class QuestionFeedbackResource(resources.ModelResource):
     class Meta:
         model = QuestionFeedback

class MessageResource(resources.ModelResource):
     class Meta:
         model = Message
