import React from 'react';
import Pool from '../components/pool';
import Fighter from '../components/fighter';
import PageTemplate from '../common/pageTemplate';
import pauseButton from '../images/pause_button.png';
import playButton from '../images/play_button.png';
import autoPlayButton from '../images/auto_play_button.png';
import { CellState, GameBoard } from '../components/gameBoard';
import { Navigate } from 'react-router-dom'
import { Maybe, MaybeType, just, nothing } from '../common/types/maybe';
import { MaybeLoad, MaybeLoadType, loaded, notFound, uninitialised, waiting } from '../common/types/load';
import axios from 'axios';
import Game from '../components/game';
import GameDetails from '../components/gameDetails';

class PoolFighterCard extends React.Component<Fighter> {
    render(): JSX.Element {
        return (
            <div className="PoolFighterCard">
                <b>{this.props.name}</b>
                <p>wins: {this.props.wins}</p>
                <p>loss: {this.props.losses}</p>
                <p>draws: {this.props.draws}</p>
            </div>
        )
    }
}

class PoolGame extends React.Component<
    {
        cellStates: CellState[],
        playerOne: Fighter,
        playerTwo: Fighter
    }
> {
    render() {
        var state: CellState[] = []

        this.props.cellStates.forEach(cellState => {
            state.push(cellState)
        })
        return (
            <div className="GameBoardSpace">
                <b>X: {this.props.playerOne.name}</b>
                <GameBoard cells={state} />
                <b>0: {this.props.playerTwo.name}</b>
            </div>

        )
    }
}

class PoolGameList extends React.Component<{ games: Game[], ackGamesLoaded: () => void }> {
    state: {
        gameboards: JSX.Element[]
        mountState: number
        gamesLoaded: boolean
    } = {
            gameboards: [],
            mountState: 0,
            gamesLoaded: false
        }

    updateGames(): void {
        const initialMountState = Math.random()
        this.setState({ mountState: initialMountState, gamesLoaded: false })

        this.props.games.forEach(game => {
            console.log("Game found!", game)
            axios.get(`/api/game/${game.id}/details/`, {
                withCredentials: true
            })
                .then((res) => {

                    if (initialMountState !== this.state.mountState) {
                        console.log("A different mount state was set")
                        return
                    }

                    const data = res.data as GameDetails
                    const cell_states: CellState[] = []

                    data.cell_details.map((detail => (
                        cell_states[detail.grid_index] = detail.state
                    )))

                    console.log(`Data of mount state ${initialMountState}`, data)
                    console.log("Cell Details", data.cell_details)
                    this.setState(
                        function (prevState: Readonly<{ gameboards: JSX.Element[] }>, _) {
                            return {
                                gameboards: prevState.gameboards.concat(<PoolGame
                                    cellStates={cell_states}
                                    playerOne={data.player_one}
                                    playerTwo={data.player_two}
                                    key={`${data.player_one.name} ${data.player_two.name}`}
                                />)
                            }
                        })
                })
                .catch((err) => {
                    console.log(err)
                })
        });
    }

    componentDidMount(): void {
        this.updateGames()
    }

    // Checks whether all the games are loaded
    componentDidUpdate(): void {
        if (this.state.gameboards.length === this.props.games.length
            && !this.state.gamesLoaded) {
            this.setState({ gamesLoaded: true })
            this.props.ackGamesLoaded()
        }
    }

    render(): JSX.Element {
        const gameboards: JSX.Element[] = [...this.state.gameboards]

        // Check the right number of boards have been retrieved
        if (gameboards.length < this.props.games.length) {
            return <p>Loading gameboards</p>
        }

        gameboards.sort((a, b) => (a.key && b.key ? a.key > b.key ? 1 : -1 : 0))

        return (
            <div className="PoolGameList">
                {gameboards}
            </div>
        )
    }
}

class PoolInfo extends React.Component<{ currentPool: Pool, ackGamesLoaded: () => void }> {
    state: {
        fighters: MaybeLoad<Fighter[]>
        games: MaybeLoad<Game[]>
    } = {
            fighters: uninitialised(),
            games: uninitialised()
        }

    getFighters(): void {
        this.setState({ fighters: waiting() })

        axios.get(`/api/pool/${this.props.currentPool.id}/fighters`, {
            withCredentials: true
        })
            .then((res) => {
                const fighters = res.data as Fighter[]

                console.log(fighters)
                this.setState({ fighters: loaded<Fighter[]>(fighters) })
            })
            .catch((err) => {
                this.setState({ fighters: notFound() })
                console.log(err)
            })
    }

    getGames(): void {
        this.setState({ games: uninitialised() })

        axios.get(`/api/pool/${this.props.currentPool.id}/games`, {
            withCredentials: true
        })
            .then((res) => {
                const games = res.data as Game[]

                console.log(games)
                this.setState({ games: loaded<Game[]>(games) })
            })
            .catch((err) => {
                this.setState({ games: notFound() })
                console.log(err)
            })
    }

    componentDidMount(): void {
        this.getFighters()
        this.getGames()
    }

    componentDidUpdate(prevProps: Readonly<{ currentPool: Pool; ackGamesLoaded: () => void; }>, prevState: Readonly<{}>, snapshot?: any): void {
        if (prevProps.currentPool !== this.props.currentPool) {
            this.getFighters()
            this.getGames()
        }
    }

    render(): JSX.Element {

        var fighterCards: JSX.Element[] = []
        var currentElement: JSX.Element

        switch (this.state.fighters.type) {
            case MaybeLoadType.NotFound:
                currentElement = <p>Unable to find fighters</p>
                break;
            case MaybeLoadType.Loaded:
                switch (this.state.games.type) {
                    case MaybeLoadType.NotFound:
                        const currentFighters = this.state.fighters.value
                        currentFighters.forEach((fighter, index) => {
                            fighterCards.push(
                                <PoolFighterCard key={index} {...fighter} />
                            )
                        })

                        console.log(fighterCards)
                        currentElement = <div className='PoolFighterCardList'>{fighterCards}</div>
                        break
                    case MaybeLoadType.Loaded:
                        currentElement = <PoolGameList
                            games={this.state.games.value}
                            ackGamesLoaded={this.props.ackGamesLoaded}
                        />
                        break
                    default:
                        currentElement = <p>We be a loading</p>

                }
                break;
            default:
                currentElement = <p>Loading fighters</p>
        }

        return (
            <div className='PoolInfo'>
                <div className='PoolInfoTitle'>
                    <b>{this.props.currentPool.id}</b>
                    <p>Generation: {this.props.currentPool.generation}</p>
                </div>
                {currentElement}
            </div>
        )
    }
}

class NewPoolInfo extends React.Component<{ onSubmit: (event: any) => void }> {
    state: {
        poolSize: number
    } = {
            poolSize: 10
        }

    render(): JSX.Element {
        return (
            <form method="post" className='NewPoolInfo' onSubmit={this.props.onSubmit}>
                <b>New Pool</b>
                <div>
                    <label htmlFor='PoolSize' className='PoolSize'>Pick Pool Size:</label>
                    <input name="fighterNumber" type="number" id="PoolSize" defaultValue="10" min="10" max="100" />
                </div>
                <input type="submit" className='NewPoolSubmit' />
            </form>
        )
    }
}

class PoolRow extends React.Component<{
    currentPool: Pool,
    onPoolSelectButton: (event: any) => void
}> {
    render(): JSX.Element {
        return (
            <button onClick={this.props.onPoolSelectButton}>{this.props.currentPool.id}</button>
        )
    }
}

class PoolList extends React.Component<{
    pools: Pool[]
    onPoolSelectionFunc: (event: any, index: number) => void
}> {
    render(): JSX.Element {
        const rows: JSX.Element[] = []

        this.props.pools.forEach((pool, index) => {
            var onPoolSelectionButton: (event: any) => void =
                event => { this.props.onPoolSelectionFunc(event, index) }

            rows.push(
                <PoolRow
                    key={index}
                    currentPool={pool}
                    onPoolSelectButton={onPoolSelectionButton}
                />
            )
        });
        return (
            <div className='PoolList'>
                <b>Your Pools</b>
                {rows}
            </div>
        )
    }
}

class PoolVideoButtons extends React.Component<{
    onPlayButton: (event: any) => void
    onAutoPlayButton: (event: any) => void
    onPauseButton: (event: any) => void
}> {
    render(): JSX.Element {
        return (
            <div className='PoolButtons'>
                <button onClick={this.props.onPauseButton}>
                    <img src={pauseButton} alt="pause" />
                </button>
                <button onClick={this.props.onPlayButton}>
                    <img src={playButton} alt="play" />
                </button>
                <button onClick={this.props.onAutoPlayButton}>
                    <img src={autoPlayButton} alt="auto play" />
                </button>

            </div>
        )
    }
}

class NewPoolButton extends React.Component<{ onNewPoolButton: (event: any) => void }> {
    render(): JSX.Element {
        return (
            <div className='NewPoolButton'>
                <button onClick={this.props.onNewPoolButton}>New Pool</button>
            </div>
        )
    }
}

class PoolSideBar extends React.Component<{
    pools: Pool[]
    onPlayButton: (event: any) => void
    onAutoPlayButton: (event: any) => void
    onPauseButton: (event: any) => void
    onNewPoolButton: (event: any) => void
    onPoolSelectionFunc: (event: any, index: number) => void
}> {
    render(): JSX.Element {
        return (
            <div className='PoolSideBar'>
                <PoolList
                    pools={this.props.pools}
                    onPoolSelectionFunc={this.props.onPoolSelectionFunc}
                />
                <NewPoolButton onNewPoolButton={this.props.onNewPoolButton} />
                <PoolVideoButtons
                    onPlayButton={this.props.onPlayButton}
                    onAutoPlayButton={this.props.onAutoPlayButton}
                    onPauseButton={this.props.onPauseButton}
                />
            </div>
        )
    }
}

class Pools extends PageTemplate {

    state: {
        pools: MaybeLoad<Pool[]>
        current_pool_index: Maybe<number>
        currentUser: MaybeLoad<string>
        gamesLoaded: MaybeLoad<null>
        autoPlayRunning: boolean
        playAutoGame: boolean
    } = {
            pools: uninitialised(),
            current_pool_index: nothing(),
            currentUser: uninitialised(),
            gamesLoaded: uninitialised(),
            autoPlayRunning: false,
            playAutoGame: false
        }

    updatePoolData(): void {
        this.setState({ pools: waiting() })
        axios.get('/api/pool', {
            withCredentials: true
        })
            .then((res) => {
                const newPools = res.data as Pool[]

                if (newPools.length > 0 && this.state.current_pool_index.type === MaybeType.Nothing) {
                    this.setState({ current_pool_index: just<number>(0) })
                } else {
                    console.log("No pools were loaded")
                }

                this.setState({ pools: loaded<Pool[]>(newPools) })
            })
            .catch((err) => {
                console.log(err)
                this.setState({
                    current_pool_index: nothing(),
                    pools: notFound(),
                })
            })
    }

    onNewPoolSubmit(event: any) {
        event.preventDefault()

        const formData = new FormData(event.target)
        const formJson = Object.fromEntries(formData.entries())

        axios.post('/api/pool/', {
            fighter_number: formJson.fighterNumber
        }, {
            withCredentials: true
        })
            .then((res) => {
                console.log("New Pool", res)
                this.updatePoolData()
            })
            .catch((err) => {
                console.log(err)
            })
        // TODO Call a single update after the generation is created
    }

    onGamesLoaded() {
        this.setState({
            gamesLoaded: loaded(null)
        })
    }

    playRound() {
        if (this.state.pools.type !== MaybeLoadType.Loaded) {
            return
        }

        // Check if games have been loaded
        if (this.state.gamesLoaded.type === MaybeLoadType.Waiting
            || this.state.gamesLoaded.type === MaybeLoadType.NotFound) {
            return
        }

        if (this.state.current_pool_index.type === MaybeType.Just) {
            const currentPool = this.state.pools.value[this.state.current_pool_index.value]

            axios.put(`/api/pool/${currentPool.id}/`, undefined, {
                withCredentials: true
            })
                .then(() => {
                    this.updatePoolData()
                })
                .catch((err) => {
                    console.log(err)
                })
        }

        this.setState({
            gamesLoaded: waiting()
        })
    }

    onPlayButton(event: any) {
        event.preventDefault()

        this.playRound()
    }

    enableAutoPlay() {
        this.setState({ playAutoGame: true })
    }

    onAutoPlayButton(event: any) {
        event.preventDefault()

        if (this.state.autoPlayRunning) {
            return
        }

        this.setState({ autoPlayRunning: true })

        this.enableAutoPlay = this.enableAutoPlay.bind(this)
        this.enableAutoPlay()
    }

    onPauseButton(event: any) {
        event.preventDefault()

        if (!this.state.autoPlayRunning) {
            return
        }

        this.setState({ autoPlayRunning: false })
    }

    onNewPoolButton(event: any) {
        event.preventDefault()

        if (this.state.current_pool_index.type === MaybeType.Nothing) {
            return
        }

        this.setState({ current_pool_index: just<number>(-1) })
    }

    onPoolSelectionFunc(event: any, index: number) {
        event.preventDefault()

        if (this.state.current_pool_index.type === MaybeType.Nothing) {
            return
        }

        // Check if gamesLoaded is complete
        if (this.state.gamesLoaded.type === MaybeLoadType.Waiting) {
            return
        }

        this.setState({ current_pool_index: just<number>(index) })
    }

    componentDidUpdate(): void {
        if (this.state.autoPlayRunning && this.state.playAutoGame) {
            this.setState({ playAutoGame: false })

            if (this.state.gamesLoaded.type === MaybeLoadType.Loaded) {
                this.playRound()
                setInterval(this.enableAutoPlay, 1000)
            } else {
                setInterval(this.enableAutoPlay, 10)
            }
        }
    }

    componentDidMount(): void {
        this.updateCurrentUser()
        this.updatePoolData()
    }

    render(): JSX.Element {

        if (this.state.currentUser.type === MaybeLoadType.NotFound) {
            return <Navigate to="/" />
        }

        var mainBlock: JSX.Element
        var sideBarBlock: JSX.Element

        switch (this.state.pools.type) {
            case MaybeLoadType.Loaded:
                const pools = this.state.pools.value
                this.onPlayButton = this.onPlayButton.bind(this)
                this.onAutoPlayButton = this.onAutoPlayButton.bind(this)
                this.onPauseButton = this.onPauseButton.bind(this)
                this.onNewPoolButton = this.onNewPoolButton.bind(this)
                this.onPoolSelectionFunc = this.onPoolSelectionFunc.bind(this)

                sideBarBlock = <PoolSideBar
                    onPlayButton={this.onPlayButton}
                    onAutoPlayButton={this.onAutoPlayButton}
                    onPauseButton={this.onPauseButton}
                    onNewPoolButton={this.onNewPoolButton}
                    onPoolSelectionFunc={this.onPoolSelectionFunc}
                    pools={pools}
                />

                if (this.state.current_pool_index.type === MaybeType.Just
                    && this.state.current_pool_index.value >= 0) {
                    this.onGamesLoaded = this.onGamesLoaded.bind(this)
                    mainBlock = <PoolInfo
                        currentPool={pools[this.state.current_pool_index.value]}
                        ackGamesLoaded={this.onGamesLoaded}
                    />
                } else {
                    this.onNewPoolSubmit = this.onNewPoolSubmit.bind(this)
                    mainBlock = <NewPoolInfo onSubmit={this.onNewPoolSubmit} />
                }
                break;
            case MaybeLoadType.NotFound:
                mainBlock = <p>Error finding pools</p>
                sideBarBlock = <PoolSideBar
                    onPlayButton={this.onPlayButton}
                    onAutoPlayButton={this.onAutoPlayButton}
                    onPauseButton={this.onPauseButton}
                    onNewPoolButton={this.onNewPoolButton}
                    onPoolSelectionFunc={this.onPoolSelectionFunc}
                    pools={[]}
                />
                break;
            default:
                mainBlock = <div />
                sideBarBlock = <PoolSideBar
                    onPlayButton={this.onPlayButton}
                    onAutoPlayButton={this.onAutoPlayButton}
                    onPauseButton={this.onPauseButton}
                    onNewPoolButton={this.onNewPoolButton}
                    onPoolSelectionFunc={this.onPoolSelectionFunc}
                    pools={[]}
                />
                break;
        }

        return (
            <div className='Pools'>
                {sideBarBlock}
                {mainBlock}
            </div>
        )
    }
}

export default Pools