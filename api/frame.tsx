import quotes from '../src/data/quotes.json';

export const config = { runtime: 'edge' };

export default async function handler(request: Request) {
    const url = new URL(request.url);
    const baseUrl = `${url.protocol}//${url.host}`;

    // 1. Pick a Random Quote ID for the NEXT state
    const randomQuote = quotes[Math.floor(Math.random() * quotes.length)];
    const imageUrl = `${baseUrl}/api/og?id=${randomQuote.id}`;
    const postUrl = `${baseUrl}/api/frame`; // Loop back to this same file on click

    // 2. Return the HTML Metatags (Farcaster Spec)
    return new Response(`
    <!DOCTYPE html>
    <html>
      <head>
        <meta property="fc:frame" content="vNext" />
        <meta property="fc:frame:image" content="${imageUrl}" />
        <meta property="fc:frame:button:1" content="🔄 New Quote" />
        <meta property="fc:frame:button:2" content="📜 Launch App" />
        <meta property="fc:frame:button:2:action" content="link" />
        <meta property="fc:frame:button:2:target" content="${baseUrl}" />
        <meta property="fc:frame:post_url" content="${postUrl}" />
        <title>Herodotus Quote</title>
      </head>
      <body>
        <h1>Herodotus Quote Frame</h1>
      </body>
    </html>
  `, {
        headers: { 'Content-Type': 'text/html' },
    });
}
