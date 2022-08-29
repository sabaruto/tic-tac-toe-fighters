import types
from unittest.mock import MagicMock, patch
from django.core import serializers
from django.http import HttpRequest, HttpResponse
from django.test import TestCase, Client
from django.urls import reverse
from google.auth.exceptions import MalformedError
from aiTicTacToe.models import *
from rest_framework.response import Response

import google
import logging
import typing
import uuid

# Create your tests here.
Choice = typing.NamedTuple("choice", grid_index=int, grid_value=CellState)

Tree = tuple[Choice, "Tree", "Tree"] | list[int]


def create_decider(tree: Tree, parent_node: Node | None = None, true_choice: bool | None = None) -> Node:

    logging.info("Decider called with Tree: %s, Parent: %s, Truth Value: %s",
                 tree, parent_node, true_choice)

    if isinstance(tree, list):

        if parent_node == None:
            raise TypeError("parent_node variable should be filled")

        if true_choice == None:
            raise TypeError("true_choice should be filled")

        leaf_node = Node.objects.create(type=NodeType.LEAF)
        Leaf.objects.create(
            node=leaf_node,
            parent=parent_node,
            choice_order={"indexes": tree},
            true_choice=true_choice
        )

        logging.debug("Created new leaf node: %s", leaf_node)
        return leaf_node

    current_choice = tree[0]
    current_node: Node

    if parent_node == None:
        current_node = Node.objects.create(type=NodeType.ROOT)
        Root.objects.create(
            node=current_node,
            grid_index=current_choice.grid_index,
            grid_value=current_choice.grid_value
        )

        logging.debug("Created new root node: %s", current_node)

    else:
        if true_choice == None:
            raise TypeError("true_choice should be filled")

        current_node = Node.objects.create(type=NodeType.BRANCH)
        Branch.objects.create(
            node=current_node,
            parent=parent_node,
            grid_index=current_choice.grid_index,
            grid_value=current_choice.grid_value,
            true_choice=true_choice
        )

        logging.debug("Created new branch node: %s", current_node)

    for current_is_true_choice in [False, True]:
        current_tree = tree[2] if current_is_true_choice else tree[1]

        create_decider(current_tree, current_node, current_is_true_choice)

    return current_node


class NodeTestCase(TestCase):
    def check_connection(self, decider):
        logging.info(
            "|------------------------------Test all nodes are properly connected----------------------------------------|")

        logging.info("Checking decision tree: %s", decider)
        root: Root = decider.container()
        unchecked_children: list[Node] = [
            root.get_child(False), root.get_child(True)]
        while len(unchecked_children) > 0:
            current_node = unchecked_children.pop()

            if current_node.type == NodeType.LEAF:
                continue

            if current_node.type == NodeType.BRANCH:
                current_branch: Branch = current_node.container()
                logging.info("Checking children of node: %s", current_node)

                # Check that both sides of the branch exists
                left_child: Node = current_branch.get_child(False)
                right_child: Node = current_branch.get_child(True)

                self.assertEqual(left_child.container().parent, current_node)
                self.assertEqual(right_child.container().parent, current_node)

                unchecked_children.append(left_child)
                unchecked_children.append(right_child)

        logging.info(
            "|------------------------------All nodes are connected!----------------------------------------|")

    def test_create_random(self):
        # Create a random decider
        decider = Node.create_random(0)
        logging.info(
            "|------------------------------Begin create_random function testing----------------------------------------|")

        child_branches = Branch.objects.filter(parent=decider)
        self.assertFalse(child_branches.exists())

        for _ in range(15):
            decider = Node.create_random(0.98)
            self.check_connection(decider)

        logging.info(
            "|------------------------------Create Random Testing Complete!----------------------------------------|")

    def test_duplicate(self):
        decider_specs: Tree = (
            Choice(2, CellState.NO_PLAYER),
            (
                Choice(1, CellState.FIRST_PLAYER),
                [1, 4, 6, 3, 8],
                [2, 7, 4, 1]
            ),
            (
                Choice(3, CellState.SECOND_PLAYER),
                [8, 3, 6, 4, 7, 1, 5],
                [4, 6, 1, 7, 8]
            )
        )

        logging.info(
            "|------------------------------Begin duplicate function testing----------------------------------------|")

        decider: Node = create_decider(decider_specs)
        decider_duplicate = Node.duplicate(decider)

        open_tuples = [(decider, decider_duplicate)]

        self.check_connection(decider_duplicate)

        logging.info(
            "|------------------------------Test duplication makes an identical decider----------------------------------------|")

        while len(open_tuples) > 0:
            current_tuple = open_tuples.pop()

            real_container = current_tuple[0].container()
            duplicate_container = current_tuple[1].container()

            self.assertTrue(real_container.similar(duplicate_container))

            if isinstance(real_container, Leaf) or isinstance(duplicate_container, Leaf):
                continue

            for true_child_choice in [True, False]:

                real_child = real_container.get_child(true_child_choice)
                duplicate_child = duplicate_container.get_child(
                    true_child_choice)

                open_tuples.append((real_child, duplicate_child))

        logging.info(
            "|------------------------------Duplicate Testing Complete!----------------------------------------|")

    def test_mutate(self):
        decider_specs: Tree = (
            Choice(2, CellState.NO_PLAYER),
            (
                Choice(1, CellState.FIRST_PLAYER),
                [1, 4, 6, 3, 8],
                [2, 7, 4, 1]
            ),
            (
                Choice(2, CellState.SECOND_PLAYER),
                [8, 3, 6, 4, 7, 1, 5],
                [4, 6, 1, 7, 8]
            )
        )

        logging.info(
            "|------------------------------Test 0% mutation doesn't affect Nodes----------------------------------------|")

        decider: Node = create_decider(decider_specs)
        decider_duplicate = Node.duplicate(decider)
        decider_duplicate.mutate(probability_of_mutation=0)

        open_tuples = [(decider, decider_duplicate)]

        while len(open_tuples) > 0:
            current_tuple = open_tuples.pop()

            real_container = current_tuple[0].container()
            duplicate_container = current_tuple[1].container()

            self.assertTrue(real_container.similar(duplicate_container))

            if isinstance(real_container, Leaf) or isinstance(duplicate_container, Leaf):
                continue

            for true_child_choice in [True, False]:

                real_child = real_container.get_child(true_child_choice)
                duplicate_child = duplicate_container.get_child(
                    true_child_choice)

                open_tuples.append((real_child, duplicate_child))

        logging.info(
            "|----------------------------Test 100% mutation affects all Nodes--------------------------------------|")

        decider_duplicate.mutate(probability_of_mutation=1)

        while len(open_tuples) > 0:
            current_tuple = open_tuples.pop()

            real_container = current_tuple[0].container()
            duplicate_container = current_tuple[1].container()

            self.assertFalse(real_container.similar(duplicate_container))

            if isinstance(real_container, Leaf) or isinstance(duplicate_container, Leaf):
                continue

            for true_child_choice in [True, False]:

                real_child = real_container.get_child(true_child_choice)
                duplicate_child = duplicate_container.get_child(
                    true_child_choice)

                open_tuples.append((real_child, duplicate_child))

        self.check_connection(decider_duplicate)
        logging.info(
            "|------------------------------Mutation Testing Complete!----------------------------------------|")

    def test_procreation(self):
        first_parent = Node.create_random(0.98)
        second_parent = Node.create_random(0.98)

        child_decider = Node.create_child(first_parent, second_parent, 0.98)

        self.check_connection(first_parent)
        self.check_connection(second_parent)
        self.check_connection(child_decider)
        logging.info(
            "|------------------------------Create Child Testing Complete!----------------------------------------|")


class GameTestCase(TestCase):

    def create_initialised_game(self) -> Game:
        new_game = Game.objects.create()
        first_fighter = Fighter.objects.create(
            name="First",
            decider=Node.create_random(0.3)
        )

        second_fighter = Fighter.objects.create(
            name="Second",
            decider=Node.create_random(0.2)
        )

        new_game.initialise(first_fighter, second_fighter)
        return new_game

    def test_create_game(self):
        new_game = Game.objects.create()
        cells = Cell.objects.filter(game=new_game)

        self.assertEquals(cells.count(), 0)
        self.assertIsNotNone(new_game)
        self.assertIsNone(new_game.pool)
        self.assertIsNone(new_game.generation)
        self.assertEquals(new_game.state, GameState.PLAYER_ONE_TURN)

    def test_initialise(self):
        new_game = self.create_initialised_game()
        cells = Cell.objects.filter(game=new_game)

        self.assertIsNone(new_game.pool)
        self.assertIsNone(new_game.generation)
        self.assertEquals(new_game.state, GameState.PLAYER_ONE_TURN)
        self.assertEquals(cells.count(), 9)

        for cell in cells:
            self.assertEquals(cell.state, CellState.NO_PLAYER)

    def test_play_empty_game(self):
        new_game = Game.objects.create()

        with self.assertRaises(UnitializedError) as ue:
            new_game.play()

    def test_play_single_move(self):
        new_game = self.create_initialised_game()

        new_game.play()
        self.assertEquals(new_game.state, GameState.PLAYER_TWO_TURN)

    def test_play_full_game(self):
        new_game = self.create_initialised_game()

        while new_game.state != GameState.COMPLETED:
            new_game.play()

        fighter_one = Plays.objects.get(game=new_game, player_one=True).fighter
        fighter_two = Plays.objects.get(
            game=new_game, player_one=False).fighter

        self.assertNotEquals(fighter_one.wins +
                             fighter_one.losses + fighter_one.draws, 0)
        self.assertEquals(fighter_one.draws, fighter_two.draws)
        self.assertEquals(fighter_one.wins, fighter_two.losses)
        self.assertEquals(fighter_one.losses, fighter_two.wins)

# TODO rewrite tests to use new functions


class PoolTestCase(TestCase):
    def setUp(self):
        self.userID = uuid.uuid4()
        self.client = Client()
        self.pool_url = reverse('poolList')
        newUser = User.objects.create(id=self.userID, name="Fake name")

    def test_pool_creation_no_fighters(self):
        # Check creating an empty pool doesn't work

        with patch('aiTicTacToe.views.authenticated_session_decoding',
                   return_value=Response(data={
                       'sub': self.userID
                   })):
            response = self.client.post(self.pool_url, {
                'fighter_number': 0
            })
        self.assertEquals(response.status_code, 400)

    def test_pool_creation_odd_fighter_number(self):
        # Check creating an odd number pool doesn't work

        with patch('aiTicTacToe.views.authenticated_session_decoding',
                   return_value=Response(data={
                       'sub': self.userID
                   })):
            response = self.client.post(self.pool_url, {
                'fighter_number': 13
            })
        self.assertEquals(response.status_code, 400)

    def test_pool_creation_negative_fighter_number(self):
        # Check creating a negative pool size doesn't work

        with patch('aiTicTacToe.views.authenticated_session_decoding',
                   return_value=Response(data={
                       'sub': self.userID
                   })):
            response = self.client.post(self.pool_url, {
                'fighter_number': -1
            })
        self.assertEquals(response.status_code, 400)

    def test_pool_creation_correct(self):
        # Check creating a normal pool works as expected

        with patch('aiTicTacToe.views.authenticated_session_decoding',
                   return_value=Response(data={
                       'sub': self.userID
                   })):
            response = self.client.post(self.pool_url, {
                'fighter_number': 10
            })

        self.assertEquals(response.status_code, 200)

        response_data = response.json()
        fighters = Fighter.objects.all()
        pools = Pool.objects.all()

        self.assertEquals(len(fighters), 10)
        self.assertEquals(len(pools), 1)

        current_pool = pools[0]

        self.assertEquals(str(current_pool.id), response_data['id'])
        self.assertEquals(response_data['generation'], 0)
        self.assertEquals(response_data['games_completed'], False)

        for fighter in fighters:
            self.assertIn(str(fighter.id), response_data['fighters'])
            self.assertEqual(fighter.wins, 0)
            self.assertEqual(fighter.draws, 0)
            self.assertEqual(fighter.losses, 0)


class PoolDetailsTestCase(TestCase):
    def MockAuthenticate(self, f: types.FunctionType, *args, **kwargs):
        with patch('aiTicTacToe.views.authenticated_session_decoding',
                   return_value=Response(data={
                       'sub': self.user.id
                   })):
            return f(*args, **kwargs)
        
    def setUp(self):
        self.client = Client()
        self.pool_url = reverse('poolList')
        self.user = User.objects.create(name="name")
        response = self.MockAuthenticate(
            self.client.post,
            self.pool_url,
            {'fighter_number': 10}
        )

        response_json = response.json()
        self.pool = Pool.objects.get(pk=response_json['id'])

    def test_get_non_existent_pool(self):
        response = self.client.get(
            reverse('poolDetails', args=(uuid.uuid4(),)))

        self.assertEquals(response.status_code, 404)

    def test_get_pool_details(self):
        response = self.client.get(
            reverse('poolDetails', args=(self.pool.id,)))

        self.assertEquals(response.status_code, 200)

    def test_put_non_existent_pool(self):
        response = self.MockAuthenticate(
            self.client.put,
            reverse('poolDetails', args=(uuid.uuid4(),))
        )

        self.assertEquals(response.status_code, 404)

    def test_put_pool(self):
        response = self.client.put(reverse('poolDetails', args=(self.pool.id,)))

        self.assertEquals(response.status_code, 200)
        self.assertEquals(self.pool.generation, 0)
        self.assertEquals(self.pool.games_completed, False)

        logging.debug("put response %s", response)

    def test_get_pool_fighters(self):
        response = self.MockAuthenticate(
            self.client.get,
            reverse('poolFighters', args=(self.pool.id,))
        )
        
        # Check the data is a list of fighters
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        
        for element in response.data:
            self.assertIn('id', element)
            self.assertIn('name', element)
            self.assertIn('wins', element)
            self.assertIn('losses', element)

        self.assertEquals(response.status_code, 200)

    def test_initialise_put_pool(self):
        get_response = self.MockAuthenticate(
            self.client.post,
            self.pool_url,
            {'fighter_number': 10}
        )
        self.assertEquals(get_response.status_code, 200)
        pool = Pool.objects.get(pk=get_response.json()['id'])

        put_response = self.client.put(reverse('poolDetails', args=(pool.id,)))
        self.assertEquals(put_response.status_code, 200)

    def test_complete_pool_games(self):
        response = self.MockAuthenticate(
            self.client.post,
            self.pool_url,
            {'fighter_number': 10}
        )
        self.assertEquals(response.status_code, 200)

        response_json = response.json()
        pool = Pool.objects.get(pk=response_json['id'])
        put_response = None

        while not pool.games_completed:
            put_response = self.MockAuthenticate(
                self.client.put,
                reverse('poolDetails', args=(pool.id,))
            )

            put_response_json = put_response.json()
            self.assertEquals(put_response.status_code, 200)

            self.assertNotEqual(len(put_response_json), 0)
            pool = Pool.objects.get(pk=response_json['id'])

        self.assertIsNotNone(put_response)
        self.assertEquals(pool.generation, 0)
        games = Game.objects.filter(pool=pool, generation=pool.generation)
        fighters = pool.fighters.all()
        found_fighters = []

        for game in games:
            game_fighters = [
                play.fighter for play in Plays.objects.filter(game=game)]
            for game_fighter in game_fighters:
                self.assertIn(game_fighter, fighters)
                self.assertNotIn(game_fighter.name, found_fighters)
                found_fighters.append(game_fighter.name)

        total_wins = 0
        total_losses = 0
        total_draws = 0
        for fighter in fighters:
            fighter_games_played = fighter.wins + fighter.draws + fighter.losses
            self.assertEquals(fighter_games_played, 1)

            total_wins += fighter.wins
            total_losses += fighter.losses
            total_draws += fighter.draws

        self.assertEquals(total_wins, total_losses)
        self.assertEquals(total_draws % 2, 0)
        self.assertEquals(total_losses + (total_draws / 2), 5)

        self.client.put(reverse('poolDetails', args=(pool.id,)))
        pool = Pool.objects.get(pk=response_json['id'])
        games = Game.objects.filter(pool=pool, generation=pool.generation)
        fighters = pool.fighters.all()

        self.assertEquals(len(games), 5)
        self.assertEquals(len(fighters), 10)

        for game in games:
            self.assertEquals(game.state, GameState.PLAYER_ONE_TURN)
            self.assertEquals(game.generation, 1)

class FighterTestCase(TestCase):

    def setUp(self):
        Node.create_random(0.98)
        Node.create_random(0.98)

    def test_get_name(self):
        new_name = Fighter.get_full_name()
        another_new_name = Fighter.get_full_name()

        self.assertIsNotNone(new_name)
        self.assertIn(" ", new_name)
        self.assertGreater(len(new_name), 3)
        self.assertNotEqual(new_name, another_new_name)

    def test_cache_creation(self):
        Fighter.cached_first_names = []
        Fighter.cached_last_names = []

        Fighter.get_full_name()
        full_cached_first_name_size = len(Fighter.cached_first_names)
        full_cached_last_name_size = len(Fighter.cached_last_names)

        self.assertGreater(full_cached_first_name_size, 0)
        self.assertGreater(full_cached_last_name_size, 0)

        Fighter.get_full_name()
        self.assertGreater(full_cached_first_name_size,
                           len(Fighter.cached_first_names))
        self.assertGreater(full_cached_last_name_size,
                           len(Fighter.cached_last_names))

    def test_name_merge(self):
        name_one_first_name = "Nancy"
        name_one_last_name = "Drew"

        name_two_first_name = "Special"
        name_two_last_name = "Person"

        name_one = "{} {}".format(name_one_first_name, name_one_last_name)
        name_two = "{} {}".format(name_two_first_name, name_two_last_name)

        merged_names = Fighter.merge_names(name_one, name_two)
        self.assertIsNotNone(merged_names)
        merged_names_first_name, merged_names_last_name = merged_names.split(
            " ")

        self.assertIn(merged_names_first_name,
                      [name_one_first_name, name_two_first_name])
        self.assertIn(merged_names_last_name,
                      [name_one_last_name, name_two_last_name])
        self.assertNotEqual(merged_names, name_one)
        self.assertNotEqual(merged_names, name_two)

    def test_comparable(self):
        first_fighter = Fighter.objects.create(
            name="First",
            wins=1,
            losses=2,
            draws=1,
            decider=Node.objects.filter(type=NodeType.ROOT)[0]
        )

        second_fighter = Fighter.objects.create(
            name="Second",
            wins=2,
            losses=1,
            draws=1,
            decider=Node.objects.filter(type=NodeType.ROOT)[1]
        )

        third_fighter = Fighter.objects.create(
            name="Third",
            wins=1,
            losses=2,
            draws=1,
            decider=Node.objects.filter(type=NodeType.ROOT)[1]
        )

        fourth_fighter = Fighter.objects.create(
            name="Fourth",
            wins=1,
            losses=1,
            draws=2,
            decider=Node.objects.filter(type=NodeType.ROOT)[1]
        )

        self.assertGreater(second_fighter, first_fighter)
        self.assertEqual(first_fighter, third_fighter)
        self.assertGreater(fourth_fighter, first_fighter)
        self.assertGreater(second_fighter, third_fighter)
        self.assertGreater(second_fighter, fourth_fighter)
        self.assertGreater(fourth_fighter, third_fighter)


class LoginAuthenticateGoogle(TestCase):
    def test_authenticate_empty_string(self):

        with self.assertRaises(MalformedError):
            info = Login.authenticateGoogleToken("")

    def test_authenticate_nonsense_string(self):

        with self.assertRaises(MalformedError):
            info = Login.authenticateGoogleToken("nonsenseinformationisgiven")

    def test_authenticate_incorrect_token(self):

        with self.assertRaises(MalformedError):
            info = Login.authenticateGoogleToken("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.NHVaYe26MbtOYhSKkoKYdFVomg4i8ZJd8_-RU8VNbftc4TSMb4bXP3l3YlNWACwyXPGffz5aXHc6lty1Y2t4SWRqGteragsVdZufDn5BlnJl9pdR_kdVFUsra2rWKEofkZeIC4yWytE58sMIihvo9H1ScmmVwBcQP6XETqYd0aSHp1gOa9RdUPDvoXQ5oqygTqVtxaDr6wUFKrKItgBMzWIdNZ6y7O9E0DhEPTbE9rfBo6KTFsHAZnMg4k68CDp2woYIaXbmYTWcvbzIuHO7_37GT79XdIwkm95QJ7hYC9RiwrV7mesbY4PAahERJawntho0my942XheVLmGwLMBkQ")


class AuthenticateSessionToken(TestCase):
    def setUp(self):
        self.user = User.objects.create(name="Name")

    def test_authenticate_empty_string(self):
        authenticated = Login.authenticateSessionToken("")

        self.assertFalse(authenticated)

    def test_authenticate_nonsense_string(self):
        authenticated = Login.authenticateSessionToken(
            "nonsenseinformationisgiven")

        self.assertFalse(authenticated)

    def test_authenticate_incorrect_token(self):
        authenticated = Login.authenticateSessionToken(
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")

        self.assertFalse(authenticated)

    def test_authenticate_old_token(self):

        jwt_token = jwt.encode({
            "sub": str(self.user.id),
            "name": self.user.name,
            "email": "fakeemail@notanemail.com",
            "image": "image?",
            "iat": int(time.time()),
            "exp": int(time.time() - 216000)
        }, settings.SESSION_SECRET)

        authenticated = Login.authenticateSessionToken(jwt_token)
        self.assertFalse(authenticated)

    def test_authenticate_wrong_data(self):

        jwt_token = jwt.encode({
            "sub": str(self.user.id),
            "nan": "Why am I here?",
            "iat": int(time.time()),
            "exp": int(time.time() + 216000)
        }, settings.SESSION_SECRET)

        authenticated = Login.authenticateSessionToken(jwt_token)
        self.assertFalse(authenticated)

    def test_authenticate_correct_data(self):

        jwt_token = jwt.encode({
            "sub": str(self.user.id),
            "name": self.user.name,
            "email": "normal@email.com",
            "image": "image?",
            "iat": int(time.time()),
            "exp": int(time.time() + 216000)
        }, settings.SESSION_SECRET)

        self.assertTrue(Login.authenticateSessionToken(jwt_token))


class TestVisualisation(TestCase):

    def setUp(self):
        Node.create_random(0.98)

    def test_heights(self):
        tree_height_one_specs: Tree = (
            Choice(1, CellState.NO_PLAYER),
            [1, 2, 3, 5, 7],
            [4, 6, 8, 0]
        )
        tree_height_one = create_decider(tree_height_one_specs)
        print(Node.draw_tree(tree_height_one))
        self.assertEqual(Node.draw_tree(tree_height_one),
                         "(1N)-------\n" +
                         "|          \\\n" +
                         "[1 2 3 5 7] [4 6 8 0]")

        tree_height_two_specs: Tree = (
            Choice(1, CellState.FIRST_PLAYER),
            (
                Choice(2, CellState.NO_PLAYER),
                [2, 4],
                [1, 8, 0, 3]
            ),
            (
                Choice(4, CellState.SECOND_PLAYER),
                [5, 7, 3],
                [1, 5, 3, 2]
            )
        )
        tree_height_two = create_decider(tree_height_two_specs)
        print(Node.draw_tree(tree_height_two))
        self.assertEqual(Node.draw_tree(tree_height_two),
                         "(1F)-----------\n" +
                         "|              \\\n" +
                         "(2N)-           (4S)---\n" +
                         "|    \\          |      \\\n"
                         "[2 4] [1 8 0 3] [5 7 3] [1 5 3 2]")
