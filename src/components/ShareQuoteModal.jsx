import React, { useRef, useState } from 'react';
import { X, Download, Share2, Copy, Check } from 'lucide-react';
import { toPng } from 'html-to-image';

const ShareQuoteModal = ({ isOpen, onClose, quote }) => {
    const [isGenerating, setIsGenerating] = useState(false);
    const [copied, setCopied] = useState(false);
    const cardRef = useRef(null);

    if (!isOpen || !quote) return null;

    const shareText = `"${quote.text}"
- ${quote.speaker}, Herodotus Histories Book ${quote.book}`;

    const handleGenerateImage = async () => {
        if (cardRef.current === null) {
            return;
        }

        setIsGenerating(true);

        try {
            const dataUrl = await toPng(cardRef.current, { cacheBust: true, backgroundColor: '#fdfbf7' });
            const link = document.createElement('a');
            link.download = `herodotus-quote-${quote.book}-${quote.speaker.replace(/\s+/g, '-').toLowerCase()}.png`;
            link.href = dataUrl;
            link.click();
        } catch (err) {
            console.error('Failed to generate image:', err);
        } finally {
            setIsGenerating(false);
        }
    };

    const copyToClipboard = async () => {
        try {
            await navigator.clipboard.writeText(shareText);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    const shareLinks = [
        { name: 'Warpcast', url: `https://warpcast.com/~/compose?text=${encodeURIComponent(shareText)}` },
        { name: 'Bluesky', url: `https://bsky.app/intent/compose?text=${encodeURIComponent(shareText)}` },
        { name: 'Twitter', url: `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}` },
    ];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-100">
                    <h2 className="font-sans text-xl font-bold text-ink flex items-center gap-2">
                        <Share2 className="w-5 h-5 text-accent" />
                        Share Quote
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500 hover:text-ink"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="overflow-y-auto p-6 space-y-8">

                    {/* Preview Area - This is what gets captured */}
                    <div className="flex justify-center">
                        <div
                            ref={cardRef}
                            className="bg-[#fdfbf7] p-8 md:p-12 rounded-none shadow-lg max-w-lg w-full border-8 border-double border-[#e5e0d5] aspect-[4/3] flex flex-col justify-center items-center text-center relative"
                            style={{ backgroundImage: 'radial-gradient(#e5e0d5 1px, transparent 1px)', backgroundSize: '20px 20px' }}
                        >
                            <div className="absolute top-4 left-4 w-8 h-8 border-t-2 border-l-2 border-accent opacity-50"></div>
                            <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-accent opacity-50"></div>
                            <div className="absolute bottom-4 left-4 w-8 h-8 border-b-2 border-l-2 border-accent opacity-50"></div>
                            <div className="absolute bottom-4 right-4 w-8 h-8 border-b-2 border-r-2 border-accent opacity-50"></div>

                            <blockquote className="font-serif text-xl md:text-3xl leading-relaxed md:leading-loose text-ink mb-6 text-justify indent-8 relative z-10">
                                {quote.text}
                            </blockquote>

                            <div className="font-sans text-accent uppercase tracking-widest text-sm md:text-base font-bold text-stone-500">
                                {quote.speaker}
                            </div>
                            <div className="font-serif text-gray-500 text-xs mt-2 italic">
                                Herodotus, Histories Book {quote.book}
                            </div>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <button
                            onClick={handleGenerateImage}
                            disabled={isGenerating}
                            className="flex items-center justify-center gap-2 w-full py-3 bg-accent text-white rounded-lg hover:bg-ink transition-colors font-sans font-medium disabled:opacity-50"
                        >
                            {isGenerating ? (
                                <span>Generating...</span>
                            ) : (
                                <>
                                    <Download className="w-5 h-5" />
                                    Download Image
                                </>
                            )}
                        </button>

                        <button
                            onClick={copyToClipboard}
                            className="flex items-center justify-center gap-2 w-full py-3 border border-gray-200 text-ink rounded-lg hover:bg-gray-50 transition-colors font-sans font-medium"
                        >
                            {copied ? <Check className="w-5 h-5 text-green-600" /> : <Copy className="w-5 h-5" />}
                            {copied ? 'Copied!' : 'Copy Text'}
                        </button>
                    </div>

                    {/* Social Links */}
                    <div className="border-t border-gray-100 pt-6">
                        <p className="text-sm text-gray-500 font-sans mb-4 text-center">Or share directly to:</p>
                        <div className="flex justify-center gap-4">
                            {shareLinks.map((link) => (
                                <a
                                    key={link.name}
                                    href={link.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        window.open(link.url, '_blank', 'width=550,height=420');
                                    }}
                                    className="px-4 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-ink font-sans text-sm transition-colors border border-gray-200"
                                >
                                    {link.name}
                                </a>
                            ))}
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default ShareQuoteModal;
