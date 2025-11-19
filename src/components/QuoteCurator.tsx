import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Typography,
  Box,
  Paper,
  LinearProgress
} from '@mui/material';
import {
  ArrowBack,
  ArrowForward,
  Check,
  Close,
  Star,
  SkipNext,
  Book
} from '@mui/icons-material';

const QuoteCurator = () => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [quotes, setQuotes] = useState([]);
  const [filteredQuotes, setFilteredQuotes] = useState([]);
  const [verifiedQuotes, setVerifiedQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [speakerInput, setSpeakerInput] = useState('');
  const [notes, setNotes] = useState('');
  const [selectedBook, setSelectedBook] = useState('');
  const [availableBooks, setAvailableBooks] = useState([]);
  const [saveStatus, setSaveStatus] = useState({
    lastSaved: null,
    error: null
  });

  // Save to localStorage as backup
  const saveToLocalStorage = (quotes) => {
    try {
      const saveData = {
        verified_quotes: quotes,
        lastSaved: new Date().toISOString()
      };
      localStorage.setItem('herodotus-quote-backup', JSON.stringify(saveData));
      setSaveStatus(prev => ({
        ...prev,
        lastSaved: saveData.lastSaved,
        error: null
      }));
    } catch (error) {
      console.error('Error saving to localStorage:', error);
      setSaveStatus(prev => ({
        ...prev,
        error: 'Failed to save backup'
      }));
    }
  };

  // Load quotes and saved verifications
  useEffect(() => {
    const loadQuotes = async () => {
      try {
        setLoading(true);
        const data = await fetch('/data/quotes.json')
          .then(res => res.json());
        
        console.log("Loaded quotes:", data.slice(0, 2));
        setQuotes(data);
        
        const books = [...new Set(data.map(quote => quote.book))].sort();
        setAvailableBooks(books);
        setSelectedBook(books[0]);
        
        try {
          // Try loading from file first
          const verifiedData = await fetch('/data/verified_quotes.json')
            .then(res => res.json());
          setVerifiedQuotes(verifiedData.verified_quotes || []);
          
          // Update save status
          setSaveStatus(prev => ({
            ...prev,
            lastSaved: new Date().toISOString()
          }));
        } catch (e) {
          console.log('No existing verified quotes found in file, checking localStorage...');
          // Try loading from localStorage as backup
          const localBackup = localStorage.getItem('herodotus-quote-backup');
          if (localBackup) {
            const backupData = JSON.parse(localBackup);
            setVerifiedQuotes(backupData.verified_quotes || []);
            setSaveStatus(prev => ({
              ...prev,
              lastSaved: backupData.lastSaved
            }));
          }
        }
      } catch (error) {
        console.error('Error loading quotes:', error);
        setError('Failed to load quotes. Error: ' + error.message);
      } finally {
        setLoading(false);
      }
    };
  
    loadQuotes();
  }, []);

  // Filter quotes when book selection changes
  useEffect(() => {
    if (selectedBook) {
      const filtered = quotes.filter(quote => quote.book === selectedBook);
      setFilteredQuotes(filtered);
      setCurrentIndex(0);
    }
  }, [selectedBook, quotes]);

  // Handle verification of quotes
  const handleVerify = async (verified, significant = false) => {
    if (currentIndex >= filteredQuotes.length) return;
    
    const quote = filteredQuotes[currentIndex];
    const verifiedQuote = {
      text: quote.text,
      speaker: speakerInput || quote.speaker,
      book: quote.book,
      context_before: quote.context_before,
      context_after: quote.context_after,
      historically_significant: significant,
      notes: notes,
      verification_date: new Date().toISOString(),
      original_attribution: {
        speaker: quote.speaker,
        confidence: quote.confidence,
        pattern_matched: quote.pattern_matched
      }
    };

    const newVerifiedQuotes = [...verifiedQuotes, verifiedQuote];
    setVerifiedQuotes(newVerifiedQuotes);

    try {
      // Save to file
      console.log('Attempting to save to data/verified_quotes.json');
      await window.fs.writeFile(
        'data/verified_quotes.json',  // Changed from 'public/data/verified_quotes.json'
        JSON.stringify({ verified_quotes: newVerifiedQuotes }, null, 2)
      );
      console.log('Successfully saved to file');
      
      // Backup to localStorage
      saveToLocalStorage(newVerifiedQuotes);
    } catch (error) {
      console.error('Error saving verified quotes:', error);
      // If file save fails, at least try localStorage
      saveToLocalStorage(newVerifiedQuotes);
    }

    setSpeakerInput('');
    setNotes('');
    setCurrentIndex(prev => prev + 1);
  };

  // Export verified quotes to file
  const exportVerifiedQuotes = () => {
    const dataStr = JSON.stringify({
      verified_quotes: verifiedQuotes,
      export_date: new Date().toISOString()
    }, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `herodotus-verified-quotes-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <Box p={2}>Loading quotes...</Box>;
  }

  if (error) {
    return <Box p={2} color="error.main">{error}</Box>;
  }

  const currentQuote = filteredQuotes[currentIndex];

  if (!currentQuote) {
    return (
      <Box p={2} textAlign="center">
        <Typography>No more quotes to verify in Book {selectedBook}</Typography>
        {currentIndex > 0 && (
          <Button
            variant="contained"
            sx={{ mt: 2 }}
            onClick={() => setCurrentIndex(0)}
          >
            Return to Beginning of Book
          </Button>
        )}
      </Box>
    );
  }

  const verifiedCount = verifiedQuotes.filter(q => q.book === selectedBook).length;
  const progress = (verifiedCount / filteredQuotes.length) * 100;

  return (
    <Box sx={{ maxWidth: '1000px', mx: 'auto', p: 2 }}>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h5">Quote Curator</Typography>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <FormControl sx={{ minWidth: 200 }}>
                  <InputLabel>Select Book</InputLabel>
                  <Select
                    value={selectedBook}
                    onChange={(e) => setSelectedBook(e.target.value)}
                    label="Select Book"
                  >
                    {availableBooks.map((book) => (
                      <MenuItem key={book} value={book}>
                        Book {book}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Button
                  variant="outlined"
                  onClick={exportVerifiedQuotes}
                  sx={{ ml: 1 }}
                >
                  Export Verified
                </Button>
              </Box>
            </Box>

            {/* Progress Tracking */}
            <Box sx={{ mt: 2, mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">
                  Progress: {verifiedCount} / {filteredQuotes.length} quotes verified
                </Typography>
                {saveStatus.lastSaved && (
                  <Typography variant="body2" color="text.secondary">
                    Last saved: {new Date(saveStatus.lastSaved).toLocaleString()}
                  </Typography>
                )}
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={progress}
              />
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Book />
                <Typography>
                  Book {selectedBook}: Quote {currentIndex + 1} of {filteredQuotes.length}
                </Typography>
              </Box>
              <Box>
                <Button
                  onClick={() => setCurrentIndex(prev => Math.max(0, prev - 1))}
                  disabled={currentIndex === 0}
                >
                  <ArrowBack />
                </Button>
                <Button
                  onClick={() => setCurrentIndex(prev => Math.min(filteredQuotes.length - 1, prev + 1))}
                  disabled={currentIndex === filteredQuotes.length - 1}
                >
                  <ArrowForward />
                </Button>
              </Box>
            </Box>

            <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
              <Typography color="text.secondary">{currentQuote.context_before}</Typography>
              <Typography sx={{ my: 2, fontWeight: 500 }}>"{currentQuote.text}"</Typography>
              <Typography color="text.secondary">{currentQuote.context_after}</Typography>
            </Paper>

            <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 500 }}>Parser Attribution</Typography>
              <Typography>Speaker: {currentQuote.speaker || 'Unknown'}</Typography>
              <Typography>Confidence: {(currentQuote.confidence * 100).toFixed(1)}%</Typography>
              <Typography>Pattern: {currentQuote.pattern_matched}</Typography>
            </Paper>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Verify or correct speaker..."
                value={speakerInput}
                onChange={(e) => setSpeakerInput(e.target.value)}
                fullWidth
              />
              <TextField
                label="Add notes..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                fullWidth
              />
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, pt: 2 }}>
              <Button
                variant="contained"
                color="error"
                startIcon={<Close />}
                onClick={() => handleVerify(false)}
              >
                Reject
              </Button>
              <Button
                variant="outlined"
                startIcon={<SkipNext />}
                onClick={() => setCurrentIndex(prev => prev + 1)}
              >
                Skip
              </Button>
              <Button
                variant="contained"
                color="primary"
                startIcon={<Check />}
                onClick={() => handleVerify(true)}
              >
                Verify
              </Button>
              <Button
                variant="contained"
                color="secondary"
                startIcon={<Star />}
                onClick={() => handleVerify(true, true)}
              >
                Mark Significant
              </Button>
            </Box>

            {saveStatus.error && (
              <Typography color="error" sx={{ mt: 2 }}>
                {saveStatus.error}
              </Typography>
            )}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default QuoteCurator;