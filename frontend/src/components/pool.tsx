class Pool {
    id: string;
    generation: number;
    fighters: string[];
    games_completed: boolean;

    constructor(id: string, generation: number, fighters: string[], games_completed: boolean) {
        this.id = id;
        this.generation = generation;
        this.fighters = fighters;
        this.games_completed = games_completed
    }
}

export default Pool;