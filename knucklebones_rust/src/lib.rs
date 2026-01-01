#[pyo3::pymodule]
mod knucklebones_rust {
    use pyo3::prelude::*;
    use rand::prelude::*;
    use std::collections::HashMap;

    #[pyclass]
    struct Knucklebones {
        boards: Vec<Board>,
        columns_number: usize,
        rows_number: usize,
        max_dice_value: u8,
        dice_value: u8,
        current_player: usize,
        max_number_of_elements: usize,
    }

    #[pyclass]
    #[derive(Clone)]
    struct Board {
        board: Vec<Vec<u8>>,
        number_of_elements: usize,
    }

    #[pymethods]
    impl Board {
        #[new]
        fn new(columns_number: usize, rows_number: usize) -> Self {
            Self {
                board: vec![vec![0; rows_number]; columns_number],
                number_of_elements: 0,
            }
        }

        fn get_board(&self) -> Vec<Vec<u8>> {
            self.board.clone()
        }
    }

    #[pymethods]
    impl Knucklebones {
        #[new]
        fn new(columns_number: usize, rows_number: usize, max_dice_value: u8) -> Self {
            Self {
                boards: vec![
                    Board::new(columns_number, rows_number),
                    Board::new(columns_number, rows_number),
                ],
                columns_number: columns_number,
                rows_number: rows_number,
                max_dice_value: max_dice_value,
                dice_value: rand::rng().random_range(1..=max_dice_value),
                current_player: 0,
                max_number_of_elements: columns_number * rows_number,
            }
        }

        fn add_value_to_column(
            &mut self,
            board_index: usize,
            player_index: usize,
            value: u8,
        ) -> PyResult<bool> {
            let player_board = &mut self.boards[player_index].board;
            let column = &mut player_board[board_index];
            for i in 0..self.rows_number {
                if column[i] == 0 {
                    column[i] = value;
                    self.boards[player_index].number_of_elements += 1;
                    return Ok(true);
                }
            }
            return Ok(false);
        }

        fn remove_value_from_column(
            &mut self,
            board_index: usize,
            player_index: usize,
            value: u8,
        ) -> PyResult<bool> {
            let player_board = &mut self.boards[player_index];
            let column = &mut player_board.board[board_index];
            let mut found = false;
            for i in 0..self.rows_number {
                if column[i] == value {
                    column[i] = 0;
                    player_board.number_of_elements -= 1;
                    found = true;
                }
            }
            return Ok(found);
        }

        fn make_move(&mut self, board_index: usize) -> PyResult<bool> {
            // Check if the board index is valid
            if board_index >= self.boards[self.current_player].board.len() {
                return Ok(false);
            }

            // Check if the board is full
            if self.boards[self.current_player].number_of_elements >= self.max_number_of_elements {
                return Ok(false);
            }

            // Add the value to the column for the current player
            let success =
                self.add_value_to_column(board_index, self.current_player, self.dice_value)?;
            if !success {
                return Ok(false);
            }

            // Remove for the other players the value in the column
            self.remove_value_from_column(
                board_index,
                self.get_other_player(self.current_player),
                self.dice_value,
            )?;

            // Switch to the other player and roll the dice again
            self.current_player = self.get_other_player(self.current_player);
            self.dice_value = rand::rng().random_range(1..=self.max_dice_value);

            return Ok(true);
        }

        fn get_score(&self, player_index: usize) -> usize {
            // The score is the sum of the values in the board
            // If a value is repeated in a column, the total is multiplied by the number of repetitions
            // e.g. if the column has the values 6, 6, 5 the score is (6+6)*2 + 5 = 29
            let board = &self.boards[player_index].board;
            let mut score: usize = 0;
            for column in 0..self.columns_number {
                let mut value_dict = HashMap::new();
                for row in 0..self.rows_number {
                    value_dict.insert(
                        board[column][row],
                        value_dict.get(&board[column][row]).unwrap_or(&0) + 1,
                    );
                }
                for (value, count) in value_dict {
                    score += value as usize * count * count;
                }
            }
            return score;
        }

        fn get_heuristic_score(&self, player_index: usize) -> i64 {
            let player_score = self.get_score(player_index) as i64;
            let other_score = self.get_score(self.get_other_player(player_index)) as i64;
            return player_score - other_score;
        }

        fn is_game_over(&self) -> bool {
            // The game is over if the boards are full
            for player_index in 0..self.boards.len() {
                if self.boards[player_index].number_of_elements >= self.max_number_of_elements {
                    return true;
                }
            }
            return false;
        }

        fn get_other_player(&self, player_index: usize) -> usize {
            if player_index == 0 {
                return 1;
            }
            return 0;
        }

        fn get_current_player(&self) -> usize {
            self.current_player
        }

        fn get_dice_value(&self) -> u8 {
            self.dice_value
        }

        fn get_boards(&self) -> Vec<Board> {
            self.boards.clone()
        }

        fn get_number_of_elements(&self, player_index: usize) -> usize {
            self.boards[player_index].number_of_elements
        }

        fn set_dice_value(&mut self, dice_value: u8) {
            self.dice_value = dice_value;
        }

        fn display_board(&self, player_index: usize) -> String {
            let board = &self.boards[player_index].board;
            let mut result = String::new();
            for row in 0..self.rows_number {
                for column in 0..self.columns_number {
                    result.push_str(&board[column][self.rows_number - row - 1].to_string());
                    result.push_str(" ");
                }
                result.push_str("\n");
            }
            result
        }

        fn is_column_full(&self, column: usize, player_index: usize) -> bool {
            self.boards[player_index].board[column]
                .iter()
                .all(|&x| x != 0)
        }

        fn get_available_columns(&self, player_index: usize) -> Vec<usize> {
            let mut available_columns = Vec::new();
            for column in 0..self.columns_number {
                if !self.is_column_full(column, player_index) {
                    available_columns.push(column);
                }
            }
            available_columns
        }

        // Possible moves for the current player
        // Combinations of columns that can be used x possible dice values
        fn get_possible_moves(&self) -> Vec<(u8, Vec<usize>)> {
            let mut possible_moves = HashMap::new();
            for column in 0..self.columns_number {
                if self.is_column_full(column, self.current_player) {
                    continue;
                }
                for dice_value in 1..=self.max_dice_value {
                    possible_moves
                        .entry(dice_value)
                        .or_insert(Vec::new())
                        .push(column);
                }
            }
            let mut possible_moves_vec = possible_moves
                .into_iter()
                .collect::<Vec<(u8, Vec<usize>)>>();
            possible_moves_vec.sort_by_key(|(dice_value, _)| *dice_value);
            possible_moves_vec
        }

        fn encode_game(&self) -> String {
            let mut encoded_game = String::new();
            for board in &self.boards {
                for row in &board.board {
                    for value in row {
                        encoded_game.push_str(&value.to_string());
                        encoded_game.push_str(",");
                    }
                }
            }
            encoded_game.push_str(&self.dice_value.to_string());
            encoded_game.push_str(",");
            encoded_game.push_str(&self.current_player.to_string());
            encoded_game
        }

        fn copy(&self) -> Self {
            Self {
                boards: self.boards.clone(),
                columns_number: self.columns_number,
                rows_number: self.rows_number,
                max_dice_value: self.max_dice_value,
                dice_value: self.dice_value,
                current_player: self.current_player,
                max_number_of_elements: self.max_number_of_elements,
            }
        }
    }
}
