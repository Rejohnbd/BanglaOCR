'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';

const EMOJIS = ['🎮', '🚀', '⚡', '🎨', '🎵', '🏆', '🌟', '💎'];

interface CardType {
  id: number;
  emoji: string;
  isFlipped: boolean;
  isMatched: boolean;
}

export function MemoryGame() {
  const [cards, setCards] = useState<CardType[]>([]);
  const [flippedIndices, setFlippedIndices] = useState<number[]>([]);
  const [moves, setMoves] = useState(0);
  const [matches, setMatches] = useState(0);
  const [isLocked, setIsLocked] = useState(false);

  useEffect(() => {
    initializeGame();
  }, []);

  const initializeGame = () => {
    const shuffled = [...EMOJIS, ...EMOJIS]
      .sort(() => Math.random() - 0.5)
      .map((emoji, index) => ({
        id: index,
        emoji,
        isFlipped: false,
        isMatched: false,
      }));
    setCards(shuffled);
    setFlippedIndices([]);
    setMoves(0);
    setMatches(0);
    setIsLocked(false);
  };

  const handleCardClick = (index: number) => {
    if (isLocked) return;
    if (cards[index].isFlipped || cards[index].isMatched) return;
    if (flippedIndices.length === 2) return;

    const newCards = [...cards];
    newCards[index].isFlipped = true;
    setCards(newCards);

    const newFlipped = [...flippedIndices, index];
    setFlippedIndices(newFlipped);

    if (newFlipped.length === 2) {
      setMoves(moves + 1);
      setIsLocked(true);

      const [first, second] = newFlipped;
      if (cards[first].emoji === cards[second].emoji) {
        setTimeout(() => {
          const matchedCards = [...cards];
          matchedCards[first].isMatched = true;
          matchedCards[second].isMatched = true;
          setCards(matchedCards);
          setFlippedIndices([]);
          setMatches(matches + 1);
          setIsLocked(false);
        }, 300);
      } else {
        setTimeout(() => {
          const resetCards = [...cards];
          resetCards[first].isFlipped = false;
          resetCards[second].isFlipped = false;
          setCards(resetCards);
          setFlippedIndices([]);
          setIsLocked(false);
        }, 1000);
      }
    }
  };

  const isComplete = matches === EMOJIS.length;

  return (
    <Card variant="bordered" className="mt-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">
          🎮 Memory Game • {moves} moves • {matches}/{EMOJIS.length} pairs
        </h3>
        <button
          onClick={initializeGame}
          className="text-xs text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
        >
          New Game
        </button>
      </div>

      {isComplete && (
        <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/30 rounded-xl text-center">
          <p className="text-green-700 dark:text-green-400 text-sm font-medium">
            🎉 Congratulations! You completed the game in {moves} moves!
          </p>
        </div>
      )}

      <div className="grid grid-cols-4 gap-2">
        {cards.map((card, index) => (
          <button
            key={card.id}
            onClick={() => handleCardClick(index)}
            disabled={card.isMatched}
            className={`h-16 flex items-center justify-center text-2xl rounded-xl transition-all duration-200 ${
              card.isFlipped || card.isMatched
                ? 'bg-gradient-to-br from-indigo-500 to-purple-500 text-white shadow-lg scale-95'
                : 'bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700'
            }`}
          >
            {card.isFlipped || card.isMatched ? card.emoji : '?'}
          </button>
        ))}
      </div>
    </Card>
  );
}
