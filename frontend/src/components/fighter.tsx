class Fighter {
    id: string;
    name: string;
    wins: number;
    losses: number;
    draws: number;

    constructor(id: string, name: string, wins: number, losses: number, draws: number) {
        this.id = id
        this.name = name;
        this.wins = wins;
        this.losses = losses;
        this.draws = draws;
    }
}

export default Fighter;