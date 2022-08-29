from django.conf import settings
from django.http import HttpRequest
import jwt
import requests
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import CellSerializer, FighterSerializer, GoogleLoginSerializer, NewGameSerializer, NewJWTTokenSeralizer, NewPoolSerializer, NodeSerializer, PlaysSerializer, GameSerializer, PoolSerializer, UserSerializer
from .models import Cell, Fighter, Game, GameState, Login, Node, Plays, Pool, StateError, User

import logging
import random


def authenticated_session_decoding(request) -> Response:
    authenticate_request = HttpRequest()
    logging.info(authenticate_request)
    logging.info(request._request)

    authenticate_request.method = 'GET'
    authenticate_request.COOKIES = request.COOKIES
    response: Response = LoginView.as_view()(request=authenticate_request)
    logging.info("login response {0}".format(response))

    if response.status_code != 200:
        return response

    session_token = response.data['session_token']
    token_data = jwt.decode(session_token, settings.SESSION_SECRET, "HS256")
    return Response(token_data)


class FighterList(generics.ListAPIView):
    queryset = Fighter.objects.all()
    serializer_class = FighterSerializer


class FighterDetails(generics.RetrieveAPIView):
    queryset = Fighter.objects.all()
    serializer_class = FighterSerializer


class CellDetails(APIView):

    def get(self, request, game_pk):
        cells = Cell.objects.filter(game=game_pk)
        serializer = CellSerializer(cells, many=True)
        return Response(serializer.data)


class PlayGame(APIView):

    def get(self, request, pk):
        try:
            game = Game.objects.get(pk=pk)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = GameSerializer(game)
        return Response(serializer.data)

    def put(self, request, pk):
        game = Game.objects.get(pk=pk)

        try:
            game.play()
        except StateError:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        return Response(status=status.HTTP_200_OK)

    def delete(self, request, pk):
        game: Game
        try:
            game = Game.objects.get(pk=pk)
        except Game.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        game.delete()
        return Response(status=status.HTTP_200_OK)

# TODO Look into fixing return dictionary issues
class GameDetails(APIView):

    def get(self, request, pk):
        try:
            game = Game.objects.get(pk=pk)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        fighter_one = Plays.objects.get(game=game, player_one=True).fighter
        fighter_two = Plays.objects.get(game=game, player_one=False).fighter
        cells_request = HttpRequest()
        cells_request.method = 'GET'
        cells_request.COOKIES = request.COOKIES


        response: Response = CellDetails.as_view()(request=cells_request, game_pk=game.id)

        if response.status_code != 200:
            return response


        returnDict = {
            "player_one": FighterSerializer(fighter_one).data,
            "player_two": FighterSerializer(fighter_two).data,
            "cell_details": response.data,
        }

        logging.info("Return data {}".format(returnDict).encode("utf-8"))

        return Response(returnDict)


class ResetGame(APIView):

    def post(self, request, pk):
        game: Game

        try:
            game = Game.objects.get(pk=pk)
        except Game.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        game.reset()

        return Response(status=status.HTTP_200_OK)


# TODO Change to use request.COOKIES. See PoolList for example
class LoginView(APIView):
    def get(self, request):
        if 'session_id' not in request.COOKIES:
            logging.warn("Request lacks session token")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        session_token = request.COOKIES['session_id']
        authenticated_token = Login.authenticateSessionToken(session_token)

        if not authenticated_token:
            logging.error("Recieved token isn't valid")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        token_serialiser = NewJWTTokenSeralizer(
            {"session_token": session_token})
        return Response(token_serialiser.data)

    def post(self, request):

        request_serializer = GoogleLoginSerializer(data=request.data)

        if not request_serializer.is_valid():
            logging.warn("Invalid payload")
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = request.data['google_jwt']

        jwt_token: str

        try:
            logging.info("Authenticating token")
            jwt_token = Login.authenticateGoogleToken(token)
        except Exception as e:
            return Response("Unable to authenticate token: %s" % e, status=status.HTTP_400_BAD_REQUEST)

        return Response({"session_token": jwt_token})


class NewGame(APIView):

    def post(self, request):

        request_serializer = NewGameSerializer(data=request.data)
        first_fighter: Fighter
        second_fighter: Fighter

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            first_fighter = Fighter.objects.get(
                pk=request_serializer.data.get('first_fighter', -1))
            second_fighter = Fighter.objects.get(
                pk=request_serializer.data.get('second_fighter', -1))
        except Fighter.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        new_game = Game.objects.create(state=GameState.PLAYER_ONE_TURN)
        new_game.initialise(first_fighter, second_fighter)
        serializer = GameSerializer(new_game)

        return Response(serializer.data)


class NewNode(APIView):

    def post(self, request):
        root = Node.create_random(probability_of_branch=0.98)
        serializer = NodeSerializer(root)
        return Response(serializer.data)


class GameList(APIView):
    def get(self, request, game_num):
        game_ids = []

        for game_index in range(game_num):
            current_game = Game.objects.create()
            game_ids.append(current_game)

        return Response(game_ids)


class PlayList(APIView):
    """
    Returns fighters connected to a game
    """

    def get(self, request, game_pk):
        try:
            plays = Plays.objects.filter(game__id__exact=game_pk)
        except Plays.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serialzer = PlaysSerializer(plays, many=True)
        return Response(serialzer.data)


class PoolList(APIView):
    def get(self, request):
        response = authenticated_session_decoding(request)

        if response.status_code != 200:
            return response

        token_data = response.data
        logging.debug("decoded token_data: {0}".format(token_data))
        user_pk = token_data['sub']

        try:
            logging.info("Getting all associated pools")
            pools = Pool.objects.filter(user=user_pk)
        except Pool.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        seralised_pools = PoolSerializer(pools, many=True)

        return Response(seralised_pools.data)

    # Create a new pool given the number of pools

    def post(self, request):
        response = authenticated_session_decoding(request)

        if response.status_code != 200:
            return response

        token_data = response.data
        logging.debug("decoded token_data: {0}".format(token_data))
        user_pk = token_data['sub']

        logging.info(request.data)
        request_serialiser = NewPoolSerializer(request.data)
        fighter_number: int

        try:
            fighter_number = request_serialiser.data.get('fighter_number', -1)
        except KeyError:
            logging.warn("Unable to find fighter number")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if (fighter_number < 2):
            logging.warn("fighter number size too small")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if (fighter_number % 2 == 1):
            logging.warn("fighter number needs to be even")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        new_pool = Pool.objects.create(user=User.objects.get(pk=user_pk))

        new_pool.initialise(fighter_number)
        pool_serializer = PoolSerializer(new_pool)

        put_request = HttpRequest()
        put_request.method = 'PUT'
        put_request.COOKIES = request.COOKIES
        response: Response = PoolDetails.as_view()(request=put_request, pk=new_pool.pk)

        if response.status_code != 200:
            return response

        return Response(pool_serializer.data)


class PoolDetails(APIView):
    def get(self, request, pk):
        try:
            pool = Pool.objects.get(pk=pk)
        except Pool.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = PoolSerializer(pool)
        return Response(serializer.data)

    def put(self, request, pk):
        # Pair off each figher
        # Odd numbers are not allowed
        try:
            pool = Pool.objects.get(pk=pk)
        except Pool.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Check if the games are completed
        if pool.games_completed:
            pool.create_new_generation()
        else:
            # Play round for each game until all games are completed
            logging.info("Play another round")
            games_query = Game.objects.filter(pool=pool)

            current_all_games_complete = True
            for game in games_query:

                if game.state == GameState.COMPLETED:
                    continue
                player_one_won, _ = game.play()
                if player_one_won == None:
                    logging.info("Game not complete: %s", game)
                    current_all_games_complete = False

            all_games_complete = current_all_games_complete
            if all_games_complete:
                logging.info("All games completed")
                pool.games_completed = True

        pool.save()

        current_games = Game.objects.filter(
            pool=pool, generation=pool.generation)
        serializer = GameSerializer(current_games, many=True)

        return Response(serializer.data)


class PoolFightersList(APIView):
    def get(self, request, pk):
        response = authenticated_session_decoding(request)

        if response.status_code != 200:
            return response

        try:
            pool = Pool.objects.get(pk=pk)
        except Pool.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        fighters = pool.fighters.all().values()
        seralizer = FighterSerializer(fighters, many=True)
        return Response(seralizer.data)


class PoolGameList(APIView):
    def get(self, request, pk):
        response = authenticated_session_decoding(request)

        if response.status_code != 200:
            return response

        try:
            pool = Pool.objects.get(pk=pk)
        except Pool.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            games = Game.objects.filter(pool=pool, generation=pool.generation)
            serializer = GameSerializer(games, many=True)
            return Response(serializer.data)
        except Game.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
