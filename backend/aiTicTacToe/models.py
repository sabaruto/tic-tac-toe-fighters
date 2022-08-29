import copy
import os
import random
import time
import uuid
from collections import namedtuple
from django.conf import settings
from django.db import models
from google.oauth2 import id_token
from google.auth.transport import requests
from functools import total_ordering
from typing import Union
import logging

import jwt


class CellState(models.IntegerChoices):
    NO_PLAYER = 0
    FIRST_PLAYER = 1
    SECOND_PLAYER = 2


class GameState(models.IntegerChoices):
    PLAYER_ONE_TURN = 0
    PLAYER_TWO_TURN = 1
    COMPLETED = 2


class NodeType(models.IntegerChoices):
    ROOT = 0
    BRANCH = 1
    LEAF = 2


class BoardPosition(models.IntegerChoices):
    TOP_LEFT = 0
    TOP_MIDDLE = 1
    TOP_RIGHT = 2
    MIDDLE_LEFT = 3
    MIDDLE_MIDDLE = 4
    MIDDLE_RIGHT = 5
    BOTTOM_LEFT = 6
    BOTTOM_MIDDLE = 7
    BOTTOM_RIGHT = 8


class Node(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    type = models.IntegerField(choices=NodeType.choices)

    @classmethod
    def new_node_helper(cls, parent, probability_of_branch, available_grid_values, available_choices, is_true_choice):
        r = random

        leaf_node = False if parent is None else r.random() > probability_of_branch

        if not leaf_node and len(list(available_grid_values.keys())) > 0:
            grid_index = r.choice(list(available_grid_values.keys()))
            grid_value = r.choice(available_grid_values[grid_index])

        new_node: Node

        if parent is None:
            new_node = Node.objects.create(type=NodeType.ROOT)
            root = Root.objects.create(
                node=new_node,
                grid_index=grid_index,
                grid_value=grid_value
            )
            logging.debug(root)

        elif leaf_node or len(list(available_grid_values.keys())) < 1:
            new_node = Node.objects.create(type=NodeType.LEAF)
            r.shuffle(available_choices)
            leaf = Leaf.objects.create(
                node=new_node,
                parent=parent,
                true_choice=is_true_choice,
                choice_order={"indexes": available_choices}
            )
            logging.debug(leaf)

            return new_node

        else:
            new_node = Node.objects.create(type=NodeType.BRANCH)
            branch = Branch.objects.create(
                node=new_node,
                parent=parent,
                grid_index=grid_index,
                grid_value=grid_value,
                true_choice=is_true_choice
            )
            logging.debug(branch)

        logging.debug("New node created: %s", new_node)

        current_probability_of_branch = probability_of_branch * probability_of_branch

        for node_is_true_choice in [True, False]:
            current_available_grid_values = copy.deepcopy(
                available_grid_values)
            current_available_choices = available_choices.copy()

            if node_is_true_choice:
                current_available_grid_values.pop(grid_index)
            else:
                chosen_list = current_available_grid_values[grid_index]
                chosen_list.remove(grid_value)
                current_available_grid_values[grid_index] = chosen_list

                if len(chosen_list) < 1:
                    current_available_grid_values.pop(grid_index)

            if node_is_true_choice != (grid_value == CellState.NO_PLAYER) and grid_index in current_available_choices:
                current_available_choices.remove(grid_index)

            Node.new_node_helper(
                new_node,
                current_probability_of_branch,
                current_available_grid_values,
                current_available_choices,
                node_is_true_choice
            )

        return new_node

    @classmethod
    def create_random(cls, probability_of_branch):
        available_grid_values = dict((i, [
            CellState.NO_PLAYER,
            CellState.FIRST_PLAYER,
            CellState.SECOND_PLAYER
        ])
            for i in range(9))
        available_choices = [i for i in range(9)]

        root = Node.new_node_helper(
            None,
            probability_of_branch,
            available_grid_values,
            available_choices,
            None
        )

        return root

    @classmethod
    def _suitable_branch(cls, node: "Node", available_grid_values) -> "Node":
        # Check that the current node is acceptable
        if node.type == NodeType.LEAF:
            return None

        container = node.container()

        if container.grid_index in available_grid_values and container.grid_value in available_grid_values[container.grid_index]:
            return node
        else:
            logging.debug(
                "current branch not suitable, finding child branches")
            child_nodes = Branch.objects.filter(parent=node)
            suitable_nodes = []
            for child_node in child_nodes:
                found_node = Node._suitable_branch(
                    child_node.node, available_grid_values)
                if found_node != None:
                    logging.debug(
                        "Found some suitable child nodes! %s", found_node)
                    suitable_nodes.append(found_node)

            if len(suitable_nodes) == 0:
                logging.debug("No child branches are suitable")
                return None
            return random.choice(suitable_nodes)

    @classmethod
    def create_child_helper(cls, parent_node: "Node", first_parent_decider: "Node", second_parent_decider: "Node", available_grid_values: int, available_choices: list[int], probability_of_branch: float):

        logging.info("Adding new branch to child decider %s", parent_node)
        # Assume that the current node is either a root or branch
        container = parent_node.container()
        r = random

        grid_index = container.grid_index
        grid_value = container.grid_value

        # Loop through the left and right choices
        for node_is_true_choice in [True, False]:
            current_available_grid_values = copy.deepcopy(
                available_grid_values)
            current_available_choices = available_choices.copy()

            if node_is_true_choice:
                current_available_grid_values.pop(grid_index)
            else:
                chosen_list = current_available_grid_values[grid_index]
                chosen_list.remove(grid_value)
                current_available_grid_values[grid_index] = chosen_list

                if len(chosen_list) < 1:
                    current_available_grid_values.pop(grid_index)

            if node_is_true_choice != (grid_value == CellState.NO_PLAYER) and grid_index in current_available_choices:
                current_available_choices.remove(grid_index)

            # Check if the current node is a leaf or not
            leaf_node = r.random() > probability_of_branch

            # Check for the suitable branch node

            logging.debug("Looking for suitable branches in %s",
                          first_parent_decider)
            first_suitable_branch = cls._suitable_branch(
                first_parent_decider, current_available_grid_values)

            logging.debug("Looking for suitable branches in %s",
                          second_parent_decider)
            second_suitable_branch = cls._suitable_branch(
                second_parent_decider, current_available_grid_values)
            chosen_branch_node: Node

            if (first_suitable_branch is None and second_suitable_branch is None) or leaf_node:
                new_node = Node.objects.create(type=NodeType.LEAF)
                r.shuffle(available_choices)
                Leaf.objects.create(
                    node=new_node,
                    parent=parent_node,
                    true_choice=node_is_true_choice,
                    choice_order={"indexes": available_choices}
                )
                logging.debug("Created new leaf branch: %s", new_node)
                logging.debug("Connected to parent: %s", parent_node)
                continue
            elif first_suitable_branch is not None and second_suitable_branch is not None:
                chosen_branch_node = r.choice(
                    [first_suitable_branch, second_suitable_branch])
            elif first_suitable_branch is not None:
                chosen_branch_node = first_suitable_branch
            else:
                chosen_branch_node = second_suitable_branch

            new_node = Node.objects.create(type=NodeType.BRANCH)
            chosen_branch: Branch = chosen_branch_node.container()
            Branch.objects.create(
                node=new_node,
                parent=parent_node,
                grid_index=chosen_branch.grid_index,
                grid_value=chosen_branch.grid_value,
                true_choice=node_is_true_choice,
            )

            logging.info("Created new branch: %s", new_node)
            logging.debug("Connected to parent: %s", parent_node)
            new_probability_of_branch = probability_of_branch * probability_of_branch

            Node.create_child_helper(new_node, first_parent_decider, second_parent_decider,
                                     current_available_grid_values, current_available_choices, new_probability_of_branch)

    @classmethod
    def create_child(cls, first_parent_decider: "Node", second_parent_decider: "Node", probability_of_branch: int):
        available_grid_values = dict((i, [
            CellState.NO_PLAYER,
            CellState.FIRST_PLAYER,
            CellState.SECOND_PLAYER
        ])
            for i in range(9))
        available_choices = [i for i in range(9)]
        r = random

        chosen_root: Root = first_parent_decider.container(
        ) if r.random() > 0.5 else second_parent_decider.container()

        # Create a new node and root
        new_node = Node.objects.create(type=NodeType.ROOT)
        new_root = Root.objects.create(
            node=new_node,
            grid_index=chosen_root.grid_index,
            grid_value=chosen_root.grid_value,
        )

        Node.create_child_helper(new_node, first_parent_decider, second_parent_decider,
                                 available_grid_values, available_choices, probability_of_branch)

        logging.info("Completed creating child: %s", new_root)
        return new_node

    @classmethod
    def draw_tree(cls, node: "Node") -> str:
        choice_type_initial = {
            CellState.FIRST_PLAYER: "F",
            CellState.SECOND_PLAYER: "S",
            CellState.NO_PLAYER: "N"
        }
        return_string = ""
        # Check if the current node is a leaf
        if hasattr(node, 'leaf_node'):
            # return string of nodes
            current_leaf: Leaf = node.container()
            indexes = current_leaf.choice_order['indexes']

            return_string = "["
            for index in indexes:
                return_string += "{} ".format(index)
            return_string = return_string[0:len(return_string)-1] + "]"
            return return_string

        # Get the strings of the children
        container: Root | Branch = node.container()
        left_child_tree = Node.draw_tree(container.get_child(False))
        right_child_tree = Node.draw_tree(container.get_child(True))

        if len(left_child_tree) == "[]":
            logging.info("No left tree information found")

        if len(right_child_tree) == "[]":
            logging.info("No right tree information found")

        # stitch child trees by returns
        left_child_tree_lines = left_child_tree.splitlines()
        right_child_tree_lines = right_child_tree.splitlines()

        largest_left_child_length = len(left_child_tree_lines[-1])
        tree_connector = "|"
        tree_connector += "".ljust(largest_left_child_length-1)
        tree_connector += "\\"

        tree_root = "({}{})".format(container.grid_index,
                                    choice_type_initial[container.grid_value])
        tree_root = tree_root.ljust(largest_left_child_length, '-')

        children_tree = ""

        for i in range(len(left_child_tree_lines)):
            current_left_child_tree_line = left_child_tree_lines[i]
            padded_left_child_tree_line = current_left_child_tree_line.ljust(
                largest_left_child_length)

            if len(right_child_tree_lines)-1 < i:
                children_tree += "{}\n".format(padded_left_child_tree_line)
                continue

            current_right_child_tree_line = right_child_tree_lines[i]
            children_tree += "{} {}\n".format(
                padded_left_child_tree_line, current_right_child_tree_line)

        if len(left_child_tree_lines) < len(right_child_tree_lines):
            for i in range(len(left_child_tree_lines)-1, len(right_child_tree_lines)):
                current_line = "{}\n".format(right_child_tree_lines[i])
                children_tree += current_line.rjust(
                    largest_left_child_length+1)

        return_string = "\n".join([tree_root, tree_connector, children_tree])

        return return_string.strip()

    def mutate(self, probability_of_mutation: float) -> None:
        self.mutate_branch(
            probability_of_mutation=probability_of_mutation, chosen_grid_values=None)
        self.mutate_leaf(
            probability_of_mutation=probability_of_mutation, available_choices=None)

    def mutate_branch(self, probability_of_mutation: float, chosen_grid_values: None or set) -> set:

        logging.info("Mutating Node %s", self.container())
        logging.info("Chosen grid values: %s", chosen_grid_values)
        available_grid_values = dict((i, [
            CellState.NO_PLAYER,
            CellState.FIRST_PLAYER,
            CellState.SECOND_PLAYER
        ])
            for i in range(9))

        if chosen_grid_values is None:
            chosen_grid_values = set()

        # More thinkthonk needed
        split_chosen_grid_values = {
            True: set(),
            False: set()
        }

        if self.type != NodeType.LEAF:
            for node_is_true in [True, False]:
                container = self.container()
                self_chosen_grid_value = (
                    container.grid_index, node_is_true, container.grid_value)

                split_chosen_grid_values[node_is_true] = copy.deepcopy(
                    chosen_grid_values)
                split_chosen_grid_values[node_is_true].add(
                    self_chosen_grid_value)

                child_node = Node.objects.get(
                    (models.Q(branch_node__parent=self)
                     & models.Q(branch_node__true_choice=node_is_true))
                    | (models.Q(leaf_node__parent=self)
                       & models.Q(leaf_node__true_choice=node_is_true))
                )

                child_node.mutate_branch(probability_of_mutation,
                                         split_chosen_grid_values[node_is_true])

        logging.debug("back to %s", self.container())
        # Merge the split_chosen_grid_values
        merged_chosen_grid_values = split_chosen_grid_values[True].union(
            split_chosen_grid_values[False])

        logging.debug("Merged Chosen grid values %s",
                      merged_chosen_grid_values)

        # Check if mutation occurs
        r = random
        mutated = r.random() < probability_of_mutation

        if not mutated:
            return chosen_grid_values

        # Check the type of node connected
        if self.type != NodeType.LEAF:

            # Apply all changes to available_grid_values
            for grid_value in merged_chosen_grid_values:
                chosen_index = grid_value[0]
                value_true = grid_value[1]
                chosen_state = grid_value[2]

                # Ignore when index has already been removed
                if not chosen_index in available_grid_values:
                    continue

                if value_true:
                    available_grid_values.pop(chosen_index)
                else:
                    chosen_list = available_grid_values[chosen_index]
                    chosen_list.remove(chosen_state)
                    available_grid_values[chosen_index] = chosen_list

                    if len(chosen_list) < 1:
                        available_grid_values.pop(chosen_index)
            container = self.container()

            logging.debug("container: %s", container)

            # Choose a different grid value and index
            grid_index = r.choice(list(available_grid_values.keys()))
            grid_value = r.choice(available_grid_values[grid_index])

            # Remove the old grid choice from merged_chosen_grid_values
            self_chosen_grid_values = {(container.grid_index, True, container.grid_value), (
                container.grid_index, False, container.grid_value)}
            merged_chosen_grid_values.difference(self_chosen_grid_values)

            container.grid_index = grid_index
            container.grid_value = grid_value
            container.save()

        return merged_chosen_grid_values

    def mutate_leaf(self, probability_of_mutation: float, available_choices: None or list):
        available_grid_values = [i for i in range(9)]

        # More thinkthonk needed
        split_chosen_grid_values = {
            True: set(),
            False: set()
        }

        available_choices = [] if available_choices == None else available_choices

        if self.type != NodeType.LEAF:
            for node_is_true in [True, False]:
                container = self.container()

                current_available_choices = available_choices.copy()
                if node_is_true != (container.grid_value == CellState.NO_PLAYER) and container.grid_index in current_available_choices:
                    current_available_choices.remove(container.grid_index)

                child_node = Node.objects.get(
                    (models.Q(branch_node__parent=self)
                     & models.Q(branch_node__true_choice=node_is_true))
                    | (models.Q(leaf_node__parent=self)
                       & models.Q(leaf_node__true_choice=node_is_true))
                )

                child_node.mutate_leaf(probability_of_mutation,
                                       split_chosen_grid_values[node_is_true])

            return
        leaf = self.container()

        r = random
        mutated = r.random() < probability_of_mutation

        if not mutated:

            # Check if available choices has changed
            old_choice_order = leaf.choice_order['indexes']

            if set(old_choice_order) == set(available_choices):
                return

        r.shuffle(available_choices)
        leaf.choice_order = {"indexes": available_choices}

    @classmethod
    def duplicate_helper(cls, current_node: 'Node', duplicate_parent: 'Node' = None, true_choice: bool = False) -> 'Node':

        duplicate_node: Node

        if current_node.type == NodeType.ROOT:
            current_root: Root = current_node.container()
            duplicate_node = Node.objects.create(type=NodeType.ROOT)
            Root.objects.create(
                node=duplicate_node,
                grid_index=current_root.grid_index,
                grid_value=current_root.grid_value,
            )
        elif current_node.type == NodeType.BRANCH:
            current_branch: Branch = current_node.container()
            duplicate_node = Node.objects.create(type=NodeType.BRANCH)
            Branch.objects.create(
                node=duplicate_node,
                parent=duplicate_parent,
                grid_index=current_branch.grid_index,
                grid_value=current_branch.grid_value,
                true_choice=true_choice
            )
        elif current_node.type == NodeType.LEAF:
            current_leaf: Leaf = current_node.container()
            duplicate_node = Node.objects.create(type=NodeType.LEAF)
            Leaf.objects.create(
                node=duplicate_node,
                parent=duplicate_parent,
                true_choice=true_choice,
                choice_order=current_leaf.choice_order
            )
            return duplicate_node
        else:
            raise TypeError("Node", current_node,
                            "has poorly defined node type:", current_node.type)

        for true_child_choice in [True, False]:

            current_container = current_node.container()

            if isinstance(current_container, Leaf):
                raise TypeError("container should not be a leaf here")

            child_node = current_container.get_child(true_child_choice)
            cls.duplicate_helper(child_node, duplicate_node, true_child_choice)

        return duplicate_node

    @classmethod
    def duplicate(cls, decider: 'Node') -> 'Node':

        if decider.type != NodeType.ROOT:
            raise TypeError(
                "Given node of type %s but expected root node", decider.type)

        return cls.duplicate_helper(decider)

    def container(self) -> Union['Root', 'Branch', 'Leaf']:
        if self.type == NodeType.ROOT:
            return self.root_node
        elif self.type == NodeType.BRANCH:
            return self.branch_node
        elif self.type == NodeType.LEAF:
            return self.leaf_node
        else:
            raise TypeError("Node hasn't been setup properly")


class Container(models.Model):
    node = models.OneToOneField(
        Node,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name='%(class)s_node'
    )

    class Meta:
        abstract = True


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    name = models.CharField(max_length=30, blank=False)


class Choice(Container):
    grid_index = models.IntegerField(choices=BoardPosition.choices)
    grid_value = models.IntegerField(choices=CellState.choices)

    class Meta:
        abstract = True

    def get_child(self, is_true_choice: bool) -> Node:
        return Node.objects.get(
            (models.Q(branch_node__parent=self.node)
             & models.Q(branch_node__true_choice=is_true_choice))
            | (models.Q(leaf_node__parent=self.node)
               & models.Q(leaf_node__true_choice=is_true_choice))
        )


class Child(Container):
    parent = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        limit_choices_to={'Leaf': None}
    )
    true_choice = models.BooleanField()

    class Meta:
        abstract = True


class Root(Choice):
    def __str__(self):
        return "Grid Index: %s Grid Value: %s" % (
            BoardPosition.choices[self.grid_index][1],
            CellState.choices[self.grid_value][1]
        )

    def similar(self, other):
        if isinstance(other, Root):
            return (self.grid_index, self.grid_value) == (other.grid_index, other.grid_value)
        return NotImplemented


class Branch(Choice, Child):
    def __str__(self):
        return "From %r Grid Index: %s Grid Value: %s" % (
            self.true_choice,
            BoardPosition.choices[self.grid_index][1],
            CellState.choices[self.grid_value][1]
        )

    def similar(self, other):
        if isinstance(other, Branch):
            return (self.grid_index, self.grid_value, self.true_choice) == (other.grid_index, other.grid_value, other.true_choice)
        return NotImplemented


class Leaf(Child):
    choice_order = models.JSONField()

    def __str__(self):
        return "From %r  Indexes: %s" % (
            self.true_choice,
            self.choice_order
        )

    def similar(self, other):
        if isinstance(other, Leaf):
            return (self.choice_order, self.true_choice) == (other.choice_order, other.true_choice)
        return NotImplemented


class Game(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pool = models.ForeignKey(
        'Pool',
        on_delete=models.SET_NULL,
        null=True,
    )

    generation = models.IntegerField(
        null=True
    )

    state = models.IntegerField(
        choices=GameState.choices,
        default=GameState.PLAYER_ONE_TURN
    )

    def initialise(self, first_fighter: "Fighter", second_fighter: "Fighter"):
        Plays.objects.create(
            game=self, fighter=first_fighter, player_one=True)
        Plays.objects.create(
            game=self, fighter=second_fighter, player_one=False)

        for index in BoardPosition:
            Cell.objects.create(
                game=self, grid_index=index, state=CellState.NO_PLAYER)

        self.save()

    def play(self):
        plays_query = Plays.objects.filter(game=self)
        nodes_query = Cell.objects.filter(game=self)

        if plays_query.count() < 1:
            raise UnitializedError("Game is not initialised")

        if self.state == GameState.COMPLETED:
            raise StateError("Game is completed")

        player_one = self.state == GameState.PLAYER_ONE_TURN
        current_plays = plays_query.get(player_one=player_one)
        current_fighter = current_plays.fighter

        grid_index = current_fighter.choose(self, player_one)
        logging.debug("Chosen grid index: %s", grid_index)
        current_node = nodes_query.get(grid_index=grid_index)

        current_node.update(player_one)

        game_complete, player_one_won, winning_indexes = self.check_complete()

        if game_complete:
            self.state = GameState.COMPLETED

            if player_one_won is not None:
                winning_fighter = plays_query.get(
                    player_one=player_one_won).fighter
                winning_fighter.wins += 1
                winning_fighter.save()

                losing_fighter = plays_query.get(
                    player_one=not player_one_won).fighter
                losing_fighter.losses += 1
                losing_fighter.save()
            else:
                fighters = [plays.fighter for plays in plays_query]
                for fighter in fighters:
                    fighter.draws += 1
                    fighter.save()
        else:
            self.state = GameState.PLAYER_TWO_TURN if player_one else GameState.PLAYER_ONE_TURN
        self.save()

        return player_one_won, winning_indexes

    def check_complete(self):
        cells = Cell.objects.filter(game=self)

        winning_states = [
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8],
            [0, 3, 6],
            [1, 4, 7],
            [2, 5, 8],
            [0, 4, 8],
            [6, 4, 2],
        ]

        for winning_indexes in winning_states:
            if (cells[winning_indexes[0]].state != CellState.NO_PLAYER
                    and cells[winning_indexes[0]].state == cells[winning_indexes[1]].state
                    and cells[winning_indexes[0]].state == cells[winning_indexes[2]].state):
                logging.info("Found winner")
                player_one_winner = cells[winning_indexes[0]
                                          ].state == CellState.FIRST_PLAYER
                return True, player_one_winner, winning_indexes

        found_no_player_cell = False
        for cell in cells:
            if cell.state == CellState.NO_PLAYER:
                found_no_player_cell = True

        if not found_no_player_cell:
            return True, None, None

        return False, None, None


class Cell(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE
    )
    grid_index = models.IntegerField(choices=BoardPosition.choices)
    state = models.IntegerField(choices=CellState.choices)

    def reset(self):
        self.state = CellState.NO_PLAYER
        self.save()

    def __str__(self):
        return "Cell - Position: %s State: %s" % (
            BoardPosition.choices[self.grid_index][1],
            CellState.choices[self.state][1]
        )

    def update(self, player_one: bool):
        if self.state != CellState.NO_PLAYER:
            return

        self.state = CellState.FIRST_PLAYER if player_one else CellState.SECOND_PLAYER
        self.save()


class Plays(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE
    )
    fighter = models.ForeignKey(
        'Fighter',
        on_delete=models.CASCADE
    )
    player_one = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['game', 'player_one'],
                name='unique_game_player_one_combination'
            )
        ]


@total_ordering
class Fighter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    wins = models.PositiveSmallIntegerField(default=0)
    losses = models.PositiveSmallIntegerField(default=0)
    draws = models.PositiveSmallIntegerField(default=0)
    decider = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        limit_choices_to={'root_node__isnull': False}
    )

    cached_first_names = []
    cached_last_names = []

    @classmethod
    def get_full_name(cls) -> str:
        cwd = os.path.dirname(__file__)
        
        # Check if the cached names are empty
        if len(Fighter.cached_first_names) == 0:
            full_first_names_file = open(
                os.path.join(cwd, "..\\data\\first_names.txt"), "r", encoding="utf-8")
            full_first_names = [line[:-1]
                                for line in full_first_names_file.readlines()]
            random.shuffle(full_first_names)
            Fighter.cached_first_names = full_first_names[:100]
            full_first_names_file.close()

        if len(Fighter.cached_last_names) == 0:
            full_last_names_file = open(
                os.path.join(cwd, "..\\data\\last_names.txt"), "r", encoding="utf-8")
            full_last_names = [line[:-1]
                               for line in full_last_names_file.readlines()]
            random.shuffle(full_last_names)
            Fighter.cached_last_names = full_last_names[:100]
            full_last_names_file.close()

        # Pop the first name from both caches
        first_name = Fighter.cached_first_names.pop()
        last_name = Fighter.cached_last_names.pop()

        return "{} {}".format(first_name, last_name)

    @classmethod
    def merge_names(cls, name_one: str, name_two: str) -> str:
        # Splits the names in two
        name_one_first_name, name_one_last_name = name_one.split(" ", 1)
        name_two_first_name, name_two_last_name = name_two.split(" ", 1)

        choose_name_one_first_name = random.random() > 1
        if choose_name_one_first_name:
            return "{} {}".format(name_one_first_name, name_two_last_name)

        return "{} {}".format(name_two_first_name, name_one_last_name)

    def choose(self, game: Game, player_one: bool):
        cells = Cell.objects.filter(game=game.pk)
        current_node: Node = self.decider
        current_leaf: Leaf
        current_cell: Cell
        decision_true: bool

        # Changes the state to be dependent on your player state:
        #   player one: Your player
        #   player two: Other player
        def normalise_state(state: CellState, player_one):
            if state == CellState.NO_PLAYER:
                return CellState.NO_PLAYER

            if player_one:
                return state

            return CellState.FIRST_PLAYER if state == CellState.SECOND_PLAYER else CellState.SECOND_PLAYER

        while True:
            # Check if the node is a leaf
            if hasattr(current_node, 'leaf_node'):
                current_leaf = Leaf.objects.get(node=current_node.id)
                logging.debug("Found Leaf!")
                break
            elif hasattr(current_node, 'branch_node'):
                current_branch = current_node.branch_node
                current_cell: Cell = cells.get(
                    grid_index=current_branch.grid_index)
                normalised_cell = normalise_state(
                    current_cell.state, player_one)
                decision_true = current_branch.grid_value == normalised_cell
            elif hasattr(current_node, 'root_node'):
                current_root = current_node.root_node
                current_cell: Cell = cells.get(
                    grid_index=current_root.grid_index)
                normalised_cell = normalise_state(
                    current_cell.state, player_one)
                decision_true = current_root.grid_value == normalised_cell
            else:
                logging.error("Node has no type!")
                break

            # Get next node
            current_container = current_node.container()

            if isinstance(current_container, Leaf):
                raise TypeError("Node should not be leaf")

            current_node = current_container.get_child(decision_true)

        # Return the first index that's free
        indexes = current_leaf.choice_order['indexes']

        logging.info("Available indexes: %s", indexes)

        for index in indexes:
            current_cell = cells.get(grid_index=index)
            if current_cell.state == CellState.NO_PLAYER:
                return index

        logging.error("No suitable choice found")
        return -1

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, Fighter):
            return 2 * self.wins - self.losses + self.draws == 2 * other.wins - other.losses + other.draws
        else:
            return super().__eq__(self, other)

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        if isinstance(other, Fighter):
            return 2 * self.wins - self.losses + self.draws < 2 * other.wins - other.losses + other.draws
        else:
            return super().__lt__(self, other)

    def __hash__(self):
        return super().__hash__()


class Pool(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    generation = models.SmallIntegerField(default=0)
    fighters = models.ManyToManyField(Fighter)
    games_completed = models.BooleanField(default=False)
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
    )

    def initialise(self, num_fighters: int):
        # Create new nodes and fighters for use in the pool
        if self.fighters.count() > 0:
            raise AssertionError("Pool already initialised")

        for _ in range(num_fighters):
            new_node = Node.create_random(probability_of_branch=0.98)

            new_fighter = Fighter.objects.create(
                name=Fighter.get_full_name(), decider=new_node)
            self.fighters.add(new_fighter)

        # Check number of fighters made
        self.setup_new_games(int(num_fighters / 2))
        self.save()

    def setup_new_games(self, num_games: int):
        logging.info("Create new games")
        fighters = list(self.fighters.all())

        if len(fighters) < 1:
            raise UnitializedError("Pool hasn't been properly initialised")

        for _ in range(num_games):
            r = random
            first_fighter_index = r.randrange(0, len(fighters))
            first_fighter = fighters.pop(first_fighter_index)

            second_fighter_index = r.randrange(0, len(fighters))
            second_fighter = fighters.pop(second_fighter_index)

            # Create the games
            game = Game.objects.create(pool=self, generation=self.generation)
            game.initialise(first_fighter, second_fighter)

        self.save()

    def create_new_generation(self):
        logging.info("Creating new generation")
        self.generation += 1
        r = random

        fighters = list(self.fighters.all())

        if len(fighters) < 1:
            raise UnitializedError("Pool hasn't been properly initialised")

        fighters.sort(reverse=True)
        r.choices(fighters)

        logging.info("Remove unfit fighters")

        target_list_length = int(len(fighters) / 2)
        while len(fighters) > target_list_length:
            weights = [i for i in range(len(fighters))]
            fighter_index_for_deletion = r.choices(
                weights, weights=weights, k=1)[0]
            fighters.pop(fighter_index_for_deletion)
            weights.pop(fighter_index_for_deletion)

        logging.info("Number of fighters left: %d", len(fighters))

        old_fighters = fighters
        new_fighters: list[Fighter] = []

        logging.info("Create new fighters")

        while len(old_fighters) + len(new_fighters) < target_list_length * 2:
            replace_strategy = "mutate" if r.random() > 0.5 else "procreate"
            new_fighter: Node

            if replace_strategy == "mutate":
                logging.debug("Creating new fighter with mutation")
                fighter_for_mutation = r.choices(
                    old_fighters, weights=weights, k=1)[0]
                decider_to_be_mutated: Node = Node.duplicate(
                    fighter_for_mutation.decider)
                decider_to_be_mutated.mutate(0.05)

                mutated_decider = decider_to_be_mutated
                new_fighter = Fighter.objects.create(
                    name=Fighter.get_full_name(),
                    decider=mutated_decider
                )
            elif replace_strategy == "procreate":
                logging.debug("Creating new fighter with procreation")
                fighters_for_procreation = r.choices(
                    old_fighters, weights=weights, k=2)
                deciders_for_procreation = [
                    fighter.decider for fighter in fighters_for_procreation]

                child_decider = Node.create_child(
                    deciders_for_procreation[0], deciders_for_procreation[1], 0.98)
                new_fighter = Fighter.objects.create(
                    name=Fighter.merge_names(
                        fighters_for_procreation[0].name, fighters_for_procreation[1].name),
                    decider=child_decider
                )

            new_fighters.append(new_fighter)

        fighters = old_fighters + new_fighters
        self.fighters.set(fighters)

        self.setup_new_games(target_list_length)
        self.games_completed = False
        logging.info("New generation set up")
        self.save()


class Login():
    @classmethod
    def authenticateSessionToken(cls, session_token: str) -> bool:
        # deserialise token
        try:
            token_data = jwt.decode(
                session_token, settings.SESSION_SECRET, "HS256", options={"require": ["sub", "name", "email", "image", "iat", "exp"]})
            logging.info("token data {}".format(token_data))

            # Check the user exists
            referenced_user_pk = token_data['sub']
            User.objects.get(pk=referenced_user_pk)

        except jwt.DecodeError as e:
            logging.error("Decode Error: {}".format(e))
            return False
        except jwt.InvalidAlgorithmError as e:
            logging.error("Error Authenticating algorithm: {}".format(e))
            return False
        except jwt.ExpiredSignatureError as e:
            logging.info("Session token expired")
            return False
        except jwt.MissingRequiredClaimError as e:
            logging.warn(
                "Valid session token missing one or more claims: {}".format(e))
            return False
        except User.DoesNotExist as e:
            logging.warn(
                "Referenced token doesn't exist: {}".format(e))
            return False

        return True

    @classmethod
    def authenticateGoogleToken(cls, google_token: str) -> dict[str, any]:
        idinfo = id_token.verify_oauth2_token(
            google_token, requests.Request(), settings.CLIENT_ID, clock_skew_in_seconds=10)

        current_user: User
        logging.info("Google info {0}".format(idinfo))

        # Check if a user with the given email is found
        if User.objects.filter(email=idinfo['email']).exists():
            logging.debug("Accessing existing user")
            current_user = User.objects.get(email=idinfo['email'])
        else:
            # Create a new user
            logging.debug("Creating a new user")
            current_user = User.objects.create(
                email=idinfo['email'], name=idinfo['name'])

        jwt_token = jwt.encode({
            "sub": str(current_user.id),
            "name": current_user.name,
            "email": current_user.email,
            "image": idinfo['picture'],
            "iat": int(time.time()),
            "exp": int(time.time() + 216000)
        }, settings.SESSION_SECRET)

        logging.info("Sending user data")
        return jwt_token


class StateError(Exception):
    pass


class UnitializedError(Exception):
    pass
