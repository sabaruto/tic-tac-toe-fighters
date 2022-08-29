export enum GameState {
    PLAYER_ONE_TURN = 0,
    PLAYER_TWO_TURN = 1,
    COMPLETED = 2,
}

export class Game {
    id: string
    state: GameState

    constructor(id: string, state: GameState) {
        this.id = id
        this.state = state
    }

}

export default Game;