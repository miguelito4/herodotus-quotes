import React, { useState, useMemo, useRef, useEffect } from 'react';
import { Search, BookOpen, Shuffle, Copy, Share2, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import Footer from './Footer.jsx';
import ShareQuoteModal from './ShareQuoteModal.jsx';

// Import data directly
import quotesData from '../data/quotes.json';
import characterMetadata from '../data/character_metadata.json';

const HerodotusExplorer = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCharacter, setSelectedCharacter] = useState(null);
  const [randomQuote, setRandomQuote] = useState(null);
  const [selectedBook, setSelectedBook] = useState('all');
  const [expandedQuotes, setExpandedQuotes] = useState(new Set());
  const [sortOrder, setSortOrder] = useState('bookAsc');
  const [showShareModal, setShowShareModal] = useState(false);
  const [sharingQuote, setSharingQuote] = useState(null);

  const books = useMemo(() => {
    const uniqueBooks = new Set(quotesData.map(quote => quote.book));
    return Array.from(uniqueBooks).sort();
  }, []);

  const filteredCharacters = useMemo(() => {
    const speakers = [...new Set(quotesData.map(q => q.speaker))].sort();
    if (!searchTerm) return [];

    const searchLower = searchTerm.toLowerCase();

    return speakers.filter(speaker => {
      // Check if speaker name matches
      if (speaker.toLowerCase().includes(searchLower)) {
        return true;
      }

      // Check if any metadata fields match
      const metadata = characterMetadata[speaker];
      if (metadata) {
        // Check standard name
        if (metadata.standardName && metadata.standardName.toLowerCase().includes(searchLower)) {
          return true;
        }
        // Check aliases
        if (metadata.aliases && metadata.aliases.some(alias => alias.toLowerCase().includes(searchLower))) {
          return true;
        }
      }

      return false;
    });
  }, [searchTerm]);

  const getCharacterQuotes = (characterName) => {
    const filteredQuotes = quotesData.filter(quote => {
      return quote.speaker === characterName && (selectedBook === 'all' || quote.book === selectedBook);
    });

    return sortQuotes(filteredQuotes);
  };

  const sortQuotes = (quotes) => {
    return [...quotes].sort((a, b) => {
      const bookA = parseInt(a.book.replace(/\D/g, ''));
      const bookB = parseInt(b.book.replace(/\D/g, ''));
      return sortOrder === 'bookAsc' ? bookA - bookB : bookB - bookA;
    });
  };

  const getRandomQuote = () => {
    const filteredQuotes = selectedBook === 'all'
      ? quotesData
      : quotesData.filter(q => q.book === selectedBook);

    const randomIndex = Math.floor(Math.random() * filteredQuotes.length);
    setRandomQuote(filteredQuotes[randomIndex]);
    setSelectedCharacter(null);
  };

  const toggleQuoteExpansion = (quoteId) => {
    const newExpanded = new Set(expandedQuotes);
    if (newExpanded.has(quoteId)) {
      newExpanded.delete(quoteId);
    } else {
      newExpanded.add(quoteId);
    }
    setExpandedQuotes(newExpanded);
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      alert('Quote copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const getWikipediaUrl = (characterName) => {
    return `https://en.wikipedia.org/wiki/${characterName.replace(/ /g, '_')}`;
  };

  const QuoteCard = ({ quote, showSpeaker = true, index }) => {
    const isExpanded = expandedQuotes.has(index);

    const shareText = `"${quote.text}"
  - ${quote.speaker}, Herodotus Histories Book ${quote.book}`;

    return (
      <div className="bg-white rounded-lg shadow-md p-6 md:p-10 mb-6">
        <div className="flex justify-between items-start mb-6">
          <div className="flex-grow">
            {showSpeaker && (
              <div className="flex items-center mb-4">
                <BookOpen className="h-6 w-6 mr-3 text-accent" />
                <span className="font-sans text-xl font-semibold text-ink">
                  {characterMetadata[quote.speaker]?.standardName || quote.speaker}
                </span>
                {characterMetadata[quote.speaker]?.wiki && (
                  <a
                    href={characterMetadata[quote.speaker].wiki}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 p-1 hover:bg-parchment rounded-full transition-colors"
                    title={`Wikipedia: ${characterMetadata[quote.speaker].standardName || quote.speaker}`}
                  >
                    <ExternalLink className="h-4 w-4 text-accent" />
                  </a>
                )}
              </div>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => copyToClipboard(quote.text)}
              className="p-2 hover:bg-parchment rounded-full transition-colors"
              title="Copy quote"
            >
              <Copy className="h-5 w-5 text-accent" />
            </button>
            <div className="relative">
              <button
                onClick={() => {
                  setSharingQuote(quote);
                  setShowShareModal(true);
                }}
                className="p-2 hover:bg-parchment rounded-full transition-colors"
                title="Share quote"
              >
                <Share2 className="h-5 w-5 text-accent" />
              </button>
            </div>
          </div>
        </div>

        <div className="relative z-10">
          <div className="mb-8 relative">
            <span className="absolute -top-4 -left-2 text-6xl text-accent opacity-20 font-serif">"</span>
            <blockquote className="font-serif text-lg leading-relaxed md:text-2xl md:leading-loose text-ink text-justify indent-8 relative z-10">
              {quote.text}
            </blockquote>
            <span className="absolute -bottom-8 -right-2 text-6xl text-accent opacity-20 font-serif">"</span>
          </div>

          <div className="flex flex-col items-end space-y-2 mt-8 border-t border-stone-300 pt-4">
            <div className="font-sans text-accent uppercase tracking-widest text-sm md:text-base font-bold">
              {characterMetadata[quote.speaker]?.standardName || quote.speaker}
            </div>
            <div className="flex items-center gap-3">
              {quote.tags && quote.tags.map(tag => (
                <span key={tag} className="px-2 py-1 bg-stone-200 text-stone-700 text-xs rounded-full font-sans uppercase tracking-wider">
                  {tag}
                </span>
              ))}
              <div className="font-serif text-gray-500 text-xs italic">
                Herodotus, Histories Book {quote.book}
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-end">
          <button
            onClick={() => toggleQuoteExpansion(index)}
            className="flex items-center text-accent hover:text-ink transition-colors font-sans text-sm"
          >
            {isExpanded ? (
              <>
                Show less <ChevronUp className="h-4 w-4 ml-1" />
              </>
            ) : (
              <>
                Show context <ChevronDown className="h-4 w-4 ml-1" />
              </>
            )}
          </button>
        </div>

        {isExpanded && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            {quote.context_before && (
              <div className="font-serif text-lg text-gray-600 mb-4">
                <span className="font-sans text-sm font-medium text-accent block mb-2">Before:</span>
                {quote.context_before}
              </div>
            )}
            {quote.context_after && (
              <div className="font-serif text-lg text-gray-600">
                <span className="font-sans text-sm font-medium text-accent block mb-2">After:</span>
                {quote.context_after}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <div className="max-w-4xl mx-auto p-6 md:p-8">
        <h1 className="font-sans text-4xl font-bold mb-8 text-ink">
          Herodotus Quote Explorer
        </h1>
        <p className="intro-text">
          <a
            href="https://en.wikipedia.org/wiki/Herodotus"
            target="_blank"
            rel="noopener"
            className="intro-link"
          >
            Herodotus
          </a>{" "}
          graced the world with <i>Histories</i>, his chronicle of the Greco-Persian Wars.
        </p>
        <p className="intro-text">
          This website enables people to search for quotes of prominent people during the wars, hopefully enticing visitors to read the book in its entirety.
        </p>
        <p className="intro-text">
          The quotes have been parsed and compiled from Project Gutenberg's text {" "}
          <a
            href="https://www.gutenberg.org/ebooks/2707"
            target="_blank"
            rel="noopener"
            className="intro-link"
          >
            Vol. 1
          </a>{", "}
          <a
            href="https://www.gutenberg.org/ebooks/2456"
            target="_blank"
            rel="noopener"
            className="intro-link"
          >
            Vol. 2
          </a>.
        </p>
        <p></p>

        {/* Search Section */}
        <div className="mb-8 space-y-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Search characters (e.g., 'Croesus', 'Darius'...)"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setSelectedCharacter(null);
              }}
              className="w-full px-4 py-3 border rounded-lg pl-12 font-sans text-lg"
            />
            <Search className="absolute left-4 top-3.5 h-6 w-6 text-gray-400" />
          </div>

          {searchTerm && (
            <div className="mt-2 bg-white rounded-lg shadow-md max-h-96 overflow-y-auto">
              {filteredCharacters.length > 0 ? (
                filteredCharacters.map(speaker => (
                  <div
                    key={speaker}
                    onClick={() => setSelectedCharacter(speaker)}
                    className="p-4 hover:bg-parchment cursor-pointer border-b last:border-b-0 transition-colors"
                  >
                    <div className="font-sans text-lg font-medium text-ink">
                      {speaker}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 text-accent font-sans">
                  No characters found matching "{searchTerm}"
                </div>
              )}
            </div>
          )}

          <div className="flex flex-wrap gap-4">
            <select
              value={selectedBook}
              onChange={(e) => setSelectedBook(e.target.value)}
              className="px-4 py-2 border rounded-lg font-sans"
            >
              <option value="all">All Books</option>
              {books.map(book => (
                <option key={book} value={book}>Book {book}</option>
              ))}
            </select>

            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value)}
              className="px-4 py-2 border rounded-lg font-sans"
            >
              <option value="bookAsc">Book (Ascending)</option>
              <option value="bookDesc">Book (Descending)</option>
            </select>

            <button
              onClick={getRandomQuote}
              className="flex items-center gap-2 px-6 py-2 bg-accent text-white rounded-lg hover:bg-ink transition-colors font-sans"
            >
              <Shuffle className="h-4 w-4" />
              Random Quote
            </button>
          </div>
        </div>

        {/* Selected Character Section */}
        {selectedCharacter && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-sans text-3xl font-bold text-ink">
                {selectedCharacter}
              </h2>
              <a
                href={getWikipediaUrl(selectedCharacter)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-accent hover:text-ink transition-colors font-sans"
              >
                Wikipedia <ExternalLink className="h-4 w-4 ml-1" />
              </a>
            </div>
            <h3 className="font-sans text-2xl font-semibold mb-6 text-ink">
              Notable Quotes
            </h3>
            {getCharacterQuotes(selectedCharacter).map((quote, index) => (
              <QuoteCard
                key={index}
                quote={quote}
                showSpeaker={false}
                index={index}
              />
            ))}
          </div>
        )}

        {/* Random Quote Display */}
        {randomQuote && !selectedCharacter && (
          <div className="mb-8">
            <h3 className="font-sans text-2xl font-semibold mb-6 text-ink">
              Random Quote
            </h3>
            <QuoteCard
              quote={randomQuote}
              index="random"
            />
          </div>
        )}

        <ShareQuoteModal
          isOpen={showShareModal}
          onClose={() => setShowShareModal(false)}
          quote={sharingQuote}
        />
      </div>
      <Footer />
    </>
  );
};

export default HerodotusExplorer;