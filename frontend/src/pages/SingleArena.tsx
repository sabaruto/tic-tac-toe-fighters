import axios from 'axios';
import React from 'react';
import { CellState, GameBoard, jsonCellProps } from '../components/gameBoard';
import Fighter from '../components/fighter';
import Nought from '../images/Nought.svg';
import Cross from '../images/Cross.svg';
import { just, maybeOf, Maybe, nothing, MaybeType } from '../common/types/maybe';
import Game, { GameState } from "../components/game";
import { NavButton } from '../common/common';

type FightProps = {
    gameId: string
}

type RightSideBarProps = {
    maybeFirstFighter: Maybe<Fighter>
    maybeSecondFighter: Maybe<Fighter>
}

type LeftSideBarProps = {
    maybeGame: Maybe<Game>
}
class LeftSideBar extends React.Component<LeftSideBarProps> {
    render() {
        let gameInfo: JSX.Element
        if (this.props.maybeGame.type === MaybeType.Just) {
            const game = this.props.maybeGame.value

            switch (game.state) {
                case GameState.COMPLETED:
                    gameInfo = <p>Completed</p>
                    break
                case GameState.PLAYER_ONE_TURN:
                    gameInfo = <p>Player Two Turn</p>
                    break
                case GameState.PLAYER_TWO_TURN:
                    gameInfo = <p>Player One Turn</p>
                    break
            }
        } else {
            gameInfo = <p>Loading Game Data</p>
        }

        return (
            <div className='leftsidebar side'>
                <div className='legend'>
                    {gameInfo}

                </div>
                <NavButton
                    to={'/select'}
                    desc={'Back'}
                    classNames={'selected'}
                />
            </div>
        )
    }
}
class RightSideBar extends React.Component<RightSideBarProps> {

    render() {
        if (this.props.maybeFirstFighter.type === MaybeType.Just
            && this.props.maybeSecondFighter.type === MaybeType.Just) {
            const firstFighter = this.props.maybeFirstFighter.value
            const secondFighter = this.props.maybeSecondFighter.value

            return (
                <div className='rightsidebar side'>
                    <div>
                        <div className='legend'>
                            <p>{firstFighter.name}: </p>
                            <img src={Cross} alt='Cross' />
                        </div>
                        <div className='legend'>
                            <p>{secondFighter.name}: </p>
                            <img src={Nought} alt='Nought' />
                        </div>
                    </div>
                </div>
            )
        }
        return (
            this.props.maybeFirstFighter.type === MaybeType.Nothing
                ? <p>First Fighter ID doesn't exist</p>
                : <p>Second Fighter iD doesn't exist</p>
        )
    }
}

export default class SingleArena extends React.Component<FightProps> {
    state: { firstFighter: Maybe<Maybe<Fighter>>, secondFighter: Maybe<Maybe<Fighter>>, interval: Maybe<NodeJS.Timer>, cells: CellState[], game: Maybe<Game> } = {
        firstFighter: nothing(),
        secondFighter: nothing(),
        interval: nothing(),
        cells: [
            CellState.Empty,
            CellState.Empty,
            CellState.Empty,
            CellState.Empty,
            CellState.Empty,
            CellState.Empty,
            CellState.Empty,
            CellState.Empty,
            CellState.Empty
        ],
        game: nothing()
    }

    async playGame() {
        try {
            // Checks if the game is still being played
            const gameResponse = await axios.get(`/api/game/${this.props.gameId}`)
            const game = gameResponse.data as Game
            this.setState({
                game: just(game)
            })

            console.log("Current Game State:", this.state.game)

            if (game.state === GameState.COMPLETED && this.state.interval.type === MaybeType.Just) {
                console.log("Game Completed")
                clearInterval(this.state.interval.value)
                return
            }

            await axios.put(`/api/game/${this.props.gameId}/`)
            const cellsresponse = await axios.get(`/api/game/${this.props.gameId}/cells`)
            console.log(cellsresponse.data)

            const cells = cellsresponse.data as jsonCellProps[]
            const newCellStates: CellState[] = []

            cells.map(cell => (
                newCellStates[cell.grid_index] = cell.state
            ))

            this.setState({
                cells: newCellStates
            }
            )

        } catch (err) {
            console.log(err)
        }
    }

    componentWillUnmount(): void {
        if (this.state.interval.type === MaybeType.Just) {
            clearInterval(this.state.interval.value)
        }

    }

    async componentDidMount(): Promise<void> {
        // Check if the fighters have been retrieved or not
        if (this.state.firstFighter.type === MaybeType.Just
            && this.state.secondFighter.type === MaybeType.Just) {
            return
        }

        console.log('Retrieving fighters')
        let firstFighterId: string = ""
        let secondFighterId: string = ""

        try {
            const playsResponse = await axios.get(`/api/plays/${this.props.gameId}/`)
            console.log(playsResponse.data)
            firstFighterId = playsResponse.data[0].fighter
            secondFighterId = playsResponse.data[1].fighter

            const fightersResponse = await axios.get('/api/fighters/')

            console.log(fightersResponse.data);
            const fighters = fightersResponse.data as Fighter[]
            const firstFighter = maybeOf(fighters.find(fighter => fighter.id === firstFighterId));
            const secondFighter = maybeOf(fighters.find(fighter => fighter.id === secondFighterId));

            let interval: NodeJS.Timer

            if (this.state.interval.type === MaybeType.Just) {
                interval = this.state.interval.value
            } else {
                interval = setInterval(() => {
                    this.playGame();
                }, 1000);
            }


            this.setState({
                firstFighter: just(firstFighter),
                secondFighter: just(secondFighter),
                interval: just(interval)
            })
        } catch (err) {
            console.log(err)
        }

    }


    loadingFighters(): JSX.Element {
        return (
            <p>Loading Fighters</p>
        )
    }

    render(): JSX.Element {
        return (
            <div className='SingleArena'>
                <header>
                    <b>Arena</b>
                </header>
                <LeftSideBar
                    maybeGame={this.state.game}
                />
                <div className='main'>
                    <GameBoard cells={this.state.cells} />
                </div>
                {
                    this.state.firstFighter.type === MaybeType.Just
                        && this.state.secondFighter.type === MaybeType.Just
                        ? <RightSideBar
                            maybeFirstFighter={this.state.firstFighter.value}
                            maybeSecondFighter={this.state.secondFighter.value} />
                        : this.loadingFighters()
                }
            </div>
        )
    }
}
