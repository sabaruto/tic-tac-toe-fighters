from rest_framework import serializers
from .models import Cell, Fighter, Game, Pool, Node, Plays, Pool, User


class CellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cell
        fields = ('grid_index', 'state')


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = '__all__'


class FighterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fighter
        fields = ('id', 'name', 'wins', 'losses', 'draws')


class PlaysSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plays
        fields = '__all__'


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = '__all__'

class PoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pool
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class NewGameSerializer(serializers.Serializer):
    first_fighter = serializers.UUIDField(required=True)
    second_fighter = serializers.UUIDField(required=True)

class NewPoolSerializer(serializers.Serializer):
    fighter_number = serializers.IntegerField(required=True)

class GoogleLoginSerializer(serializers.Serializer):
    google_jwt = serializers.StringRelatedField()

class NewJWTTokenSeralizer(serializers.Serializer):
    session_token = serializers.StringRelatedField()
