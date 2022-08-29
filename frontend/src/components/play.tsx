export class Play {
    id: string;
    game: string;
    fighter: string;
    player_one: boolean;

    constructor(id: string, game: string, fighter: string, player_one: boolean) {
        this.id = id;
        this.game = game;
        this.fighter = fighter;
        this.player_one = player_one;
    }
}

export default Play