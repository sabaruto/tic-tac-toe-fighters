import Fighter from "./fighter";
import { CellState, jsonCellProps } from "./gameBoard";

export class GameDetails {
    player_one: Fighter
    player_two: Fighter
    cell_details: jsonCellProps[];

    constructor(
        player_one: Fighter,
        player_two: Fighter,
        cell_details: jsonCellProps[],
    ) {
        this.player_one = player_one;
        this.player_two = player_two;
        this.cell_details = cell_details;

        this.cell_details = [];
    }
}

export default GameDetails