let board = null;
let game = null;
let currentPuzzle = null;
let puzzleList = [];
let gamesList = [];
let currentGamePuzzles = null;
let hintTimeout = null;
let playerNames = new Set();
let currentPuzzleAttempted = false;
let stats = {
    totalCorrect: 0,
    totalWrong: 0,
    puzzles: {}
};

async function loadPuzzles() {
    try {
        const response = await fetch('public/puzzles/index.json');
        const indexData = await response.json();
        console.log('Loaded index data:', indexData); // Debug log
        puzzleList = indexData.puzzles;
        gamesList = indexData.games;
        
        // Collect all player names from games
        gamesList.forEach(game => {
            playerNames.add(game.white);
            playerNames.add(game.black);
        });
        
        // Populate player selector
        const playerSelect = document.getElementById('playerSelect');
        [...playerNames].sort().forEach(player => {
            const option = document.createElement('option');
            option.value = player;
            option.textContent = player;
            playerSelect.appendChild(option);
        });
        
        // Populate game selector
        const gameSelect = document.getElementById('gameSelect');
        console.log('Games list:', gamesList); // Debug log
        gamesList.forEach(game => {
            const option = document.createElement('option');
            option.value = game.id;
            const date = new Date(game.timestamp * 1000);
            option.textContent = `${game.white} vs ${game.black} (${date.toLocaleDateString()})`;
            gameSelect.appendChild(option);
        });
        
        if (puzzleList.length > 0) {
            // Check if there's a puzzle ID in the URL
            const urlParams = new URLSearchParams(window.location.search);
            const puzzleId = urlParams.get('puzzle');
            
            if (puzzleId && puzzleList.includes(puzzleId)) {
                await loadPuzzle(puzzleId);
            } else {
                await loadRandomPuzzle();
            }
        }
    } catch (error) {
        console.error('Error loading puzzles:', error);
    }
}

async function filterPuzzles(puzzleIds) {
    const myMovesOnly = document.getElementById('myMovesOnly').checked;
    const selectedPlayer = document.getElementById('playerSelect').value;
    if (!myMovesOnly || !selectedPlayer) return puzzleIds;

    const filteredPuzzles = [];
    for (const puzzleId of puzzleIds) {
        try {
            const response = await fetch(`public/puzzles/${puzzleId}.json`);
            const puzzle = await response.json();
            if (puzzle.turn_player === selectedPlayer) {
                filteredPuzzles.push(puzzleId);
            }
        } catch (error) {
            console.error(`Error loading puzzle ${puzzleId}:`, error);
        }
    }
    return filteredPuzzles;
}

async function getSelectedGamePuzzles() {
    const gameSelect = document.getElementById('gameSelect');
    const selectedGameId = gameSelect.value;
    
    const basePuzzles = !selectedGameId ? puzzleList :
        gamesList.find(game => game.id === selectedGameId)?.puzzles || puzzleList;
    
    return await filterPuzzles(basePuzzles);
}

async function loadPuzzle(puzzleId) {
    try {
        const response = await fetch(`public/puzzles/${puzzleId}.json`);
        currentPuzzle = await response.json();
        setupPuzzle();
        updateGameInfo();
        // Update URL without reloading the page
        window.history.replaceState({}, '', `?puzzle=${puzzleId}`);
    } catch (error) {
        console.error('Error loading puzzle:', error);
        // If loading specific puzzle fails, load random puzzle
        await loadRandomPuzzle();
    }
}

async function loadRandomPuzzle() {
    const availablePuzzles = await getSelectedGamePuzzles();
    if (availablePuzzles.length === 0) {
        document.getElementById('status').textContent = 'No puzzles match the current filters.';
        return;
    }
    const { puzzleIds, weights } = getWeightedPuzzles(availablePuzzles);
    const puzzleId = selectWeightedRandomPuzzle(puzzleIds, weights);
    await loadPuzzle(puzzleId);
}

function setupPuzzle() {
    // Destroy existing board if it exists
    if (board) {
        board.destroy();
    }

    game = new Chess(currentPuzzle.position);
    currentPuzzleAttempted = false;
    
    const config = {
        position: currentPuzzle.position,
        draggable: true,
        onDrop: onDrop,
        pieceTheme: 'https://cdn.jsdelivr.net/npm/chessboardjs@0.0.1/www/img/chesspieces/wikipedia/{piece}.png',
        orientation: currentPuzzle.turn_color
    };
    
    board = Chessboard('board', config);
    $(window).resize(() => board.resize());
    
    updateStatus();
}

function updateStatus() {
    document.getElementById('status').textContent = '';
    document.getElementById('toMove').textContent = 
        `${game.turn() === 'w' ? 'White' : 'Black'} to move`;
}

function updateGameInfo() {
    const gameInfo = currentPuzzle.game;
    const date = new Date(gameInfo.timestamp * 1000);
    
    document.getElementById('whitePlayer').textContent = gameInfo.white;
    document.getElementById('blackPlayer').textContent = gameInfo.black;
    document.getElementById('gameDate').textContent = date.toLocaleDateString();
    document.getElementById('gameLink').href = gameInfo.url;
    document.getElementById('gamePgn').textContent = gameInfo.pgn || 'PGN not available';
    document.getElementById('moveNumber').textContent = gameInfo.move_number || 'N/A';
    
    // Remove puzzle info
    document.getElementById('puzzleInfo').textContent = '';
}

function formatTimeControl(timeControl) {
    if (!timeControl) return 'Unknown';
    
    // Handle rapid/blitz format (e.g., "180+2")
    const parts = timeControl.split('+');
    const baseTime = parseInt(parts[0]);
    const increment = parts[1] ? parseInt(parts[1]) : 0;
    
    if (isNaN(baseTime)) return 'Unknown';
    
    const minutes = Math.floor(baseTime / 60);
    if (minutes === 0) {
        return `${baseTime} sec${increment ? ` + ${increment} sec` : ''}`;
    }
    if (increment) {
        return `${minutes} min + ${increment} sec`;
    }
    return `${minutes} min`;
}

function formatResult(result) {
    if (!result) return 'Unknown';
    switch(result) {
        case "1-0": return "White wins";
        case "0-1": return "Black wins";
        case "1/2-1/2": return "Draw";
        default: return result;
    }
}

function onDrop(source, target) {
    // If the puzzle is already solved, don't allow more moves
    if (game.turn() !== currentPuzzle.turn_color[0]) {
        return 'snapback';
    }

    const move = game.move({
        from: source,
        to: target,
        promotion: 'q'
    });

    if (move === null) return 'snapback';

    const moveString = source + target;
    const expectedMoveBase = currentPuzzle.best_move.slice(0, 4);
    
    if (moveString === expectedMoveBase) {
        document.getElementById('status').textContent = 'Correct! Click "Next Puzzle" to continue.';
        // Make board read-only by setting turn to opposite color
        game.load(game.fen().replace(' w ', ' b ').replace(' b ', ' w '));
        board.position(game.fen());
        
        // Only update stats if this was the first attempt
        if (!currentPuzzleAttempted) {
            stats.totalCorrect++;
            stats.puzzles[currentPuzzle.id] = stats.puzzles[currentPuzzle.id] || { correct: 0, wrong: 0 };
            stats.puzzles[currentPuzzle.id].correct++;
            saveStats();
        }
    } else {
        document.getElementById('status').textContent = 'Incorrect move. Try again!';
        // Only count first wrong attempt
        if (!currentPuzzleAttempted) {
            stats.totalWrong++;
            stats.puzzles[currentPuzzle.id] = stats.puzzles[currentPuzzle.id] || { correct: 0, wrong: 0 };
            stats.puzzles[currentPuzzle.id].wrong++;
            saveStats();
            currentPuzzleAttempted = true;
        }
        return 'snapback';
    }
}

function showHint() {
    const currentMove = currentPuzzle.best_move;
    if (!currentMove) return;
    
    const from = currentMove.slice(0, 2);
    const to = currentMove.slice(2, 4);
    
    const fromSquare = $(`[data-square="${from}"]`);
    const toSquare = $(`[data-square="${to}"]`);
    
    fromSquare.css('background-color', 'rgba(255, 165, 0, 0.5)');
    toSquare.css('background-color', 'rgba(255, 165, 0, 0.5)');
    
    if (hintTimeout) {
        clearTimeout(hintTimeout);
    }
    
    hintTimeout = setTimeout(() => {
        fromSquare.css('background-color', '');
        toSquare.css('background-color', '');
    }, 1000);
}

document.getElementById('nextPuzzle').addEventListener('click', () => {
    loadRandomPuzzle();
});

document.getElementById('showHint').addEventListener('click', showHint);

document.getElementById('copyPgn').addEventListener('click', function() {
    const pgnText = document.getElementById('gamePgn').textContent;
    navigator.clipboard.writeText(pgnText).then(() => {
        const button = this;
        const originalText = button.innerHTML;
        button.innerHTML = '<span class="copy-text">Copied!</span>';
        button.classList.add('copied');
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy text: ', err);
    });
});

// Add event listener for game selection
document.getElementById('gameSelect').addEventListener('change', () => {
    loadRandomPuzzle();
});

// Add event listener for the checkbox
document.getElementById('myMovesOnly').addEventListener('change', () => {
    loadRandomPuzzle();
});

// Add event listener for player selection
document.getElementById('playerSelect').addEventListener('change', () => {
    loadRandomPuzzle();
});

// Add event listener for clear stats button
document.getElementById('clearStats').addEventListener('click', () => {
    if (confirm('Are you sure you want to clear all statistics?')) {
        clearStats();
    }
});

function loadStats() {
    const savedStats = localStorage.getItem('chessStats');
    if (savedStats) {
        stats = JSON.parse(savedStats);
        updateStatsDisplay();
    }
}

function saveStats() {
    localStorage.setItem('chessStats', JSON.stringify(stats));
    updateStatsDisplay();
}

function updateStatsDisplay() {
    document.getElementById('totalCorrect').textContent = stats.totalCorrect;
    document.getElementById('totalWrong').textContent = stats.totalWrong;
    const total = stats.totalCorrect + stats.totalWrong;
    const rate = total > 0 ? Math.round((stats.totalCorrect / total) * 100) : 0;
    document.getElementById('successRate').textContent = `${rate}%`;
}

function clearStats() {
    stats = {
        totalCorrect: 0,
        totalWrong: 0,
        puzzles: {}
    };
    saveStats();
}

function getWeightedPuzzles(puzzleIds) {
    // Calculate weights based on fail/success ratio
    const weights = puzzleIds.map(id => {
        const puzzleStats = stats.puzzles[id] || { correct: 0, wrong: 0 };
        const total = puzzleStats.correct + puzzleStats.wrong;
        if (total === 0) return 1; // Default weight for new puzzles
        return 1 + (puzzleStats.wrong / (total + 1)); // Add 1 to avoid division by zero
    });
    
    // Normalize weights
    const totalWeight = weights.reduce((a, b) => a + b, 0);
    const normalizedWeights = weights.map(w => w / totalWeight);
    
    return { puzzleIds, weights: normalizedWeights };
}

function selectWeightedRandomPuzzle(puzzles, weights) {
    let random = Math.random();
    let cumulativeWeight = 0;
    
    for (let i = 0; i < puzzles.length; i++) {
        cumulativeWeight += weights[i];
        if (random <= cumulativeWeight) {
            return puzzles[i];
        }
    }
    return puzzles[puzzles.length - 1];
}

// Initialize
$(document).ready(() => {
    // Update hint button text
    document.getElementById('showHint').textContent = 'Show Solution';
    loadStats();
    loadPuzzles();
}); 