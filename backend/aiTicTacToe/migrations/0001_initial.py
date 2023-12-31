# Generated by Django 4.1 on 2023-05-07 12:13

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Fighter',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120)),
                ('wins', models.PositiveSmallIntegerField(default=0)),
                ('losses', models.PositiveSmallIntegerField(default=0)),
                ('draws', models.PositiveSmallIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('generation', models.IntegerField(null=True)),
                ('state', models.IntegerField(choices=[(0, 'Player One Turn'), (1, 'Player Two Turn'), (2, 'Completed')], default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('type', models.IntegerField(choices=[(0, 'Root'), (1, 'Branch'), (2, 'Leaf')])),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('name', models.CharField(max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('node', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='%(class)s_node', serialize=False, to='aiTicTacToe.node')),
                ('grid_index', models.IntegerField(choices=[(0, 'Top Left'), (1, 'Top Middle'), (2, 'Top Right'), (3, 'Middle Left'), (4, 'Middle Middle'), (5, 'Middle Right'), (6, 'Bottom Left'), (7, 'Bottom Middle'), (8, 'Bottom Right')])),
                ('grid_value', models.IntegerField(choices=[(0, 'No Player'), (1, 'First Player'), (2, 'Second Player')])),
                ('true_choice', models.BooleanField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Leaf',
            fields=[
                ('node', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='%(class)s_node', serialize=False, to='aiTicTacToe.node')),
                ('true_choice', models.BooleanField()),
                ('choice_order', models.JSONField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Root',
            fields=[
                ('node', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='%(class)s_node', serialize=False, to='aiTicTacToe.node')),
                ('grid_index', models.IntegerField(choices=[(0, 'Top Left'), (1, 'Top Middle'), (2, 'Top Right'), (3, 'Middle Left'), (4, 'Middle Middle'), (5, 'Middle Right'), (6, 'Bottom Left'), (7, 'Bottom Middle'), (8, 'Bottom Right')])),
                ('grid_value', models.IntegerField(choices=[(0, 'No Player'), (1, 'First Player'), (2, 'Second Player')])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Pool',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('generation', models.SmallIntegerField(default=0)),
                ('games_completed', models.BooleanField(default=False)),
                ('fighters', models.ManyToManyField(to='aiTicTacToe.fighter')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='aiTicTacToe.user')),
            ],
        ),
        migrations.CreateModel(
            name='Plays',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('player_one', models.BooleanField()),
                ('fighter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='aiTicTacToe.fighter')),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='aiTicTacToe.game')),
            ],
        ),
        migrations.AddField(
            model_name='game',
            name='pool',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='aiTicTacToe.pool'),
        ),
        migrations.AddField(
            model_name='fighter',
            name='decider',
            field=models.ForeignKey(limit_choices_to={'root_node__isnull': False}, on_delete=django.db.models.deletion.CASCADE, to='aiTicTacToe.node'),
        ),
        migrations.CreateModel(
            name='Cell',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('grid_index', models.IntegerField(choices=[(0, 'Top Left'), (1, 'Top Middle'), (2, 'Top Right'), (3, 'Middle Left'), (4, 'Middle Middle'), (5, 'Middle Right'), (6, 'Bottom Left'), (7, 'Bottom Middle'), (8, 'Bottom Right')])),
                ('state', models.IntegerField(choices=[(0, 'No Player'), (1, 'First Player'), (2, 'Second Player')])),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='aiTicTacToe.game')),
            ],
        ),
        migrations.AddConstraint(
            model_name='plays',
            constraint=models.UniqueConstraint(fields=('game', 'player_one'), name='unique_game_player_one_combination'),
        ),
        migrations.AddField(
            model_name='leaf',
            name='parent',
            field=models.ForeignKey(limit_choices_to={'Leaf': None}, on_delete=django.db.models.deletion.CASCADE, to='aiTicTacToe.node'),
        ),
        migrations.AddField(
            model_name='branch',
            name='parent',
            field=models.ForeignKey(limit_choices_to={'Leaf': None}, on_delete=django.db.models.deletion.CASCADE, to='aiTicTacToe.node'),
        ),
    ]
