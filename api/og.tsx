import { ImageResponse } from '@vercel/og';
import quotes from '../src/data/quotes.json';

export const config = { runtime: 'edge' };

export default function handler(request: Request) {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    // Find quote or pick random
    let quote = quotes.find(q => q.id === id) || quotes[Math.floor(Math.random() * quotes.length)];

    return new ImageResponse(
        (
            <div style={{
                height: '100%', width: '100%', display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', backgroundColor: '#f5f5f4',
                backgroundImage: 'radial-gradient(circle at 25px 25px, #e7e5e4 2%, transparent 0%)',
                backgroundSize: '100px 100px', padding: '40px 80px',
            }}>
                <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    border: '4px double #a8a29e', padding: '40px', height: '90%', width: '100%',
                    backgroundColor: '#fafaf9', boxShadow: '10px 10px 30px rgba(0,0,0,0.1)',
                }}>
                    <div style={{
                        fontSize: quote.text.length > 200 ? 32 : 48, fontFamily: 'serif',
                        color: '#44403c', textAlign: 'center', lineHeight: 1.4, marginBottom: 20,
                    }}>
                        "{quote.text}"
                    </div>
                    <div style={{ fontSize: 24, fontFamily: 'serif', color: '#78716c', marginTop: 20, textTransform: 'uppercase', letterSpacing: 2 }}>
                        — {quote.speaker}
                    </div>
                </div>
                <div style={{ position: 'absolute', bottom: 20, fontSize: 16, color: '#a8a29e', fontFamily: 'sans-serif' }}>
                    Herodotus Explorer
                </div>
            </div>
        ),
        { width: 1200, height: 630 }
    );
}
