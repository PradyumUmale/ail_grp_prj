from flask import Flask, render_template, jsonify, request, redirect, url_for
import math

app = Flask(__name__)

# Game State Storage
game_state = {
    "mode": "connect4",       # "connect4" or "quarto"
    "board": [],
    "rows": 6,
    "cols": 7,
    "connect_n": 4,
    "turn": "human",          # "human" or "ai"
    "game_over": False,
    "winner": None,
    # Quarto-specific state
    "selected_piece": None,
    "available_pieces": []
}

# --- CONNECT FOUR LOGIC ---
def init_connect4(rows, cols, connect_n, first_player):
    global game_state
    game_state["mode"] = "connect4"
    game_state["rows"] = rows
    game_state["cols"] = cols
    game_state["connect_n"] = connect_n
    game_state["board"] = [[0 for _ in range(cols)] for _ in range(rows)]
    game_state["turn"] = first_player
    game_state["game_over"] = False
    game_state["winner"] = None

    if first_player == "ai":
        col = cols // 2
        row = rows - 1
        game_state["board"][row][col] = 2
        game_state["turn"] = "human"

def c4_winning_move(board, piece, rows, cols, connect_n):
    for r in range(rows):
        for c in range(cols - connect_n + 1):
            if all(board[r][c + i] == piece for i in range(connect_n)):
                return True
    for r in range(rows - connect_n + 1):
        for c in range(cols):
            if all(board[r + i][c] == piece for i in range(connect_n)):
                return True
    for r in range(rows - connect_n + 1):
        for c in range(cols - connect_n + 1):
            if all(board[r + i][c + i] == piece for i in range(connect_n)):
                return True
    for r in range(connect_n - 1, rows):
        for c in range(cols - connect_n + 1):
            if all(board[r - i][c + i] == piece for i in range(connect_n)):
                return True
    return False

def c4_score_position(board, piece, rows, cols, connect_n):
    score = 0
    center_col = cols // 2
    center_array = [board[r][center_col] for r in range(rows)]
    score += center_array.count(piece) * 3
    return score

def c4_minimax(board, depth, alpha, beta, maximizingPlayer, rows, cols, connect_n):
    valid_locations = [c for c in range(cols) if board[0][c] == 0]
    is_terminal = c4_winning_move(board, 1, rows, cols, connect_n) or c4_winning_move(board, 2, rows, cols, connect_n) or len(valid_locations) == 0

    if depth == 0 or is_terminal:
        if is_terminal:
            if c4_winning_move(board, 2, rows, cols, connect_n):
                return (None, 10000000)
            elif c4_winning_move(board, 1, rows, cols, connect_n):
                return (None, -10000000)
            else:
                return (None, 0)
        else:
            return (None, c4_score_position(board, 2, rows, cols, connect_n))

    if maximizingPlayer:
        value = -math.inf
        best_col = valid_locations[0]
        for col in valid_locations:
            row = next(r for r in range(rows - 1, -1, -1) if board[r][col] == 0)
            b_copy = [r[:] for r in board]
            b_copy[row][col] = 2
            new_score = c4_minimax(b_copy, depth - 1, alpha, beta, False, rows, cols, connect_n)[1]
            if new_score > value:
                value = new_score
                best_col = col
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return best_col, value
    else:
        value = math.inf
        best_col = valid_locations[0]
        for col in valid_locations:
            row = next(r for r in range(rows - 1, -1, -1) if board[r][col] == 0)
            b_copy = [r[:] for r in board]
            b_copy[row][col] = 1
            new_score = c4_minimax(b_copy, depth - 1, alpha, beta, True, rows, cols, connect_n)[1]
            if new_score < value:
                value = new_score
                best_col = col
            beta = min(beta, value)
            if alpha >= beta:
                break
        return best_col, value


# --- QUARTO LOGIC ---
def get_piece_attributes(p):
    return ((p >> 3) & 1, (p >> 2) & 1, (p >> 1) & 1, p & 1)

def init_quarto(first_player):
    global game_state
    game_state["mode"] = "quarto"
    game_state["rows"] = 4
    game_state["cols"] = 4
    game_state["board"] = [[None for _ in range(4)] for _ in range(4)]
    game_state["available_pieces"] = list(range(16))
    game_state["turn"] = "human"
    game_state["game_over"] = False
    game_state["winner"] = None
    
    if first_player == "ai":
        game_state["selected_piece"] = 0
        game_state["available_pieces"].remove(0)
    else:
        game_state["selected_piece"] = 0
        game_state["available_pieces"].remove(0)

def check_quarto_win(board):
    lines = []
    for r in range(4):
        lines.append([board[r][c] for c in range(4)])
    for c in range(4):
        lines.append([board[r][c] for r in range(4)])
    lines.append([board[i][i] for i in range(4)])
    lines.append([board[i][3 - i] for i in range(4)])

    for line in lines:
        if any(cell is None for cell in line):
            continue
        attrs = [get_piece_attributes(p) for p in line]
        for attr_idx in range(4):
            if all(attrs[i][attr_idx] == 0 for i in range(4)) or all(attrs[i][attr_idx] == 1 for i in range(4)):
                return True
    return False

def quarto_minimax(board, available_pieces, selected_piece, depth, alpha, beta, maximizing_player):
    if check_quarto_win(board):
        return (None, available_pieces[0] if available_pieces else None, 100000 if not maximizing_player else -100000)
    if len(available_pieces) == 0 or depth == 0:
        return (None, available_pieces[0] if available_pieces else None, 0)

    empty_cells = [(r, c) for r in range(4) for c in range(4) if board[r][c] is None]
    if not empty_cells:
        return (None, None, 0)

    if maximizing_player:
        max_eval = -math.inf
        best_pos = empty_cells[0]
        best_next_piece = available_pieces[0] if available_pieces else None
        
        for r, c in empty_cells:
            board[r][c] = selected_piece
            if check_quarto_win(board):
                board[r][c] = None
                return ((r, c), available_pieces[0] if available_pieces else None, 10000)
            
            for next_p in available_pieces:
                rem_pieces = [p for p in available_pieces if p != next_p]
                _, _, eval_val = quarto_minimax(board, rem_pieces, next_p, depth - 1, alpha, beta, False)
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_pos = (r, c)
                    best_next_piece = next_p
                alpha = max(alpha, eval_val)
                if beta <= alpha:
                    break
            board[r][c] = None
            if beta <= alpha:
                break
        return best_pos, best_next_piece, max_eval
    else:
        min_eval = math.inf
        best_pos = empty_cells[0]
        best_next_piece = available_pieces[0] if available_pieces else None

        for r, c in empty_cells:
            board[r][c] = selected_piece
            if check_quarto_win(board):
                board[r][c] = None
                return ((r, c), available_pieces[0] if available_pieces else None, -10000)
            
            for next_p in available_pieces:
                rem_pieces = [p for p in available_pieces if p != next_p]
                _, _, eval_val = quarto_minimax(board, rem_pieces, next_p, depth - 1, alpha, beta, True)
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_pos = (r, c)
                    best_next_piece = next_p
                beta = min(beta, eval_val)
                if beta <= alpha:
                    break
            board[r][c] = None
            if beta <= alpha:
                break
        return best_pos, best_next_piece, min_eval


# --- FLASK ROUTES ---
@app.route("/")
def index():
    return render_template("init.html")

@app.route("/connect4")
def play_connect4():
    return render_template("connect4.html")

@app.route("/quarto")
def play_quarto():
    return render_template("quarto.html")

@app.route("/get_state", methods=["GET"])
def get_state():
    return jsonify(game_state)

@app.route("/start_game", methods=["POST"])
def start_game():
    mode = request.form.get("mode", "connect4")
    first_player = request.form.get("first_player", "human")

    if mode == "connect4":
        c4_size = request.form.get("c4Size", "6,7,4").split(",")
        rows = int(c4_size[0])
        cols = int(c4_size[1])
        connect_n = int(c4_size[2])
        init_connect4(rows, cols, connect_n, first_player)
        return redirect(url_for("play_connect4"))
    elif mode == "quarto":
        init_quarto(first_player)
        return redirect(url_for("play_quarto"))

@app.route("/make_move", methods=["POST"])
def make_move():
    global game_state
    if game_state["game_over"]:
        return jsonify({"error": "Game is already over"}), 400

    data = request.get_json()

    if game_state["mode"] == "connect4":
        col = data.get("col")
        rows = game_state["rows"]
        cols = game_state["cols"]
        connect_n = game_state["connect_n"]

        if game_state["board"][0][col] != 0:
            return jsonify({"error": "Column full"}), 400

        # Human Move
        row = next(r for r in range(rows - 1, -1, -1) if game_state["board"][r][col] == 0)
        game_state["board"][row][col] = 1

        if c4_winning_move(game_state["board"], 1, rows, cols, connect_n):
            game_state["game_over"] = True
            game_state["winner"] = "Human"
            return jsonify(game_state)
        if all(game_state["board"][0][c] != 0 for c in range(cols)):
            game_state["game_over"] = True
            game_state["winner"] = "Tie"
            return jsonify(game_state)

        # AI Move
        depth = 3 if cols >= 9 else 4
        ai_col, _ = c4_minimax(game_state["board"], depth, -math.inf, math.inf, True, rows, cols, connect_n)
        if ai_col is not None and game_state["board"][0][ai_col] == 0:
            ai_row = next(r for r in range(rows - 1, -1, -1) if game_state["board"][r][ai_col] == 0)
            game_state["board"][ai_row][ai_col] = 2

            if c4_winning_move(game_state["board"], 2, rows, cols, connect_n):
                game_state["game_over"] = True
                game_state["winner"] = "AI"
                return jsonify(game_state)
            if all(game_state["board"][0][c] != 0 for c in range(cols)):
                game_state["game_over"] = True
                game_state["winner"] = "Tie"
                return jsonify(game_state)

    elif game_state["mode"] == "quarto":
        row = data.get("row")
        col = data.get("col")
        next_piece_to_give = data.get("next_piece")

        if game_state["selected_piece"] is None:
            return jsonify({"error": "No piece selected to place!"}), 400
        if game_state["board"][row][col] is not None:
            return jsonify({"error": "Cell already occupied!"}), 400

        piece_to_place = game_state["selected_piece"]
        game_state["board"][row][col] = piece_to_place

        if check_quarto_win(game_state["board"]):
            game_state["game_over"] = True
            game_state["winner"] = "Human"
            return jsonify(game_state)
        if len(game_state["available_pieces"]) == 0:
            game_state["game_over"] = True
            game_state["winner"] = "Tie"
            return jsonify(game_state)

        if next_piece_to_give not in game_state["available_pieces"]:
            return jsonify({"error": "Invalid piece selected to give AI."}), 400

        game_state["available_pieces"].remove(next_piece_to_give)

        # AI Turn
        best_pos, best_next_piece, _ = quarto_minimax(
            game_state["board"], 
            game_state["available_pieces"], 
            next_piece_to_give, 
            depth=2, 
            alpha=-math.inf, 
            beta=math.inf, 
            maximizing_player=True
        )

        if best_pos:
            ai_r, ai_c = best_pos
            game_state["board"][ai_r][ai_c] = next_piece_to_give

            if check_quarto_win(game_state["board"]):
                game_state["game_over"] = True
                game_state["winner"] = "AI"
                return jsonify(game_state)
            if len(game_state["available_pieces"]) == 0:
                game_state["game_over"] = True
                game_state["winner"] = "Tie"
                return jsonify(game_state)

            if best_next_piece is not None and best_next_piece in game_state["available_pieces"]:
                game_state["available_pieces"].remove(best_next_piece)
                game_state["selected_piece"] = best_next_piece
            else:
                game_state["selected_piece"] = game_state["available_pieces"].pop(0) if game_state["available_pieces"] else None
        else:
            empty_cells = [(r, c) for r in range(4) for c in range(4) if game_state["board"][r][c] is None]
            if empty_cells:
                ai_r, ai_c = empty_cells[0]
                game_state["board"][ai_r][ai_c] = next_piece_to_give
            game_state["selected_piece"] = game_state["available_pieces"].pop(0) if game_state["available_pieces"] else None

    return jsonify(game_state)

if __name__ == "__main__":
    app.run()