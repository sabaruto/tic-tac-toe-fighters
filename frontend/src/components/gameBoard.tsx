import React from 'react';
import Nought from '../images/Nought.svg';
import Cross from '../images/Cross.svg';
import { Maybe, nothing } from '../common/types/maybe';

export enum CellState {
    Empty = 0,
    Cross = 1,
    Nought = 2,
}

type CellProps = {
    cellState: CellState
}

export type jsonCellProps = {
    grid_index: number
    state: number
}

type gameProps = {
    cells: CellState[]
}


class Cell extends React.Component<CellProps> {
    render(): JSX.Element {
        let element: string | undefined;
        switch (this.props.cellState) {
            case (CellState.Empty):
                element = undefined
                break
            case (CellState.Cross):
                element = Cross
                break
            case (CellState.Nought):
                element = Nought
                break
        }

        return (
            <div className="Cell" style={{ background: ` url(${element})` }} />
        )
    }
}

export class GameBoard extends React.Component<gameProps> {

    state: { playerOne: boolean, completed: boolean, playerOneWinner: Maybe<Boolean>, winningIndexes: Maybe<number[]> } = {
        playerOne: true,
        completed: false,
        playerOneWinner: nothing(),
        winningIndexes: nothing(),
    }

    render(): JSX.Element {
        return (
            <ul className='board fill-ul'>
                {[0, 1, 2].map((row_index) => (
                    <li key={row_index.toString()}>
                        {[0, 1, 2].map((col_index) => (
                            <Cell
                                key={col_index}
                                cellState={this.props.cells[row_index * 3 + col_index]}
                            />
                        ))}
                    </li>
                ))}
            </ul>
        )
    }
}
