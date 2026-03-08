"""Lightweight WordPiece tokenizer for MiniLM ONNX inference.

No `transformers` dependency — loads vocab.txt directly.
Produces input_ids + attention_mask for ONNX sentence-transformer models.
"""
import re
from pathlib import Path


class WordPieceTokenizer:
    """Minimal WordPiece tokenizer compatible with all-MiniLM-L6-v2."""

    CLS_TOKEN = "[CLS]"
    SEP_TOKEN = "[SEP]"
    UNK_TOKEN = "[UNK]"
    PAD_TOKEN = "[PAD]"

    def __init__(self, vocab_path, max_length=128):
        self.max_length = max_length
        self.vocab = {}
        self.ids_to_tokens = {}
        self._load_vocab(vocab_path)
        self.cls_id = self.vocab.get(self.CLS_TOKEN, 101)
        self.sep_id = self.vocab.get(self.SEP_TOKEN, 102)
        self.unk_id = self.vocab.get(self.UNK_TOKEN, 100)
        self.pad_id = self.vocab.get(self.PAD_TOKEN, 0)

    def _load_vocab(self, vocab_path):
        """Load vocab.txt — one token per line, index = line number."""
        path = Path(vocab_path)
        with path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                token = line.strip()
                if token:
                    self.vocab[token] = idx
                    self.ids_to_tokens[idx] = token

    def _basic_tokenize(self, text):
        """Lowercase, strip accents, split on whitespace + punctuation."""
        text = text.lower().strip()
        # Insert spaces around punctuation
        text = re.sub(r"([^\w\s])", r" \1 ", text)
        return text.split()

    def _wordpiece_tokenize(self, word):
        """Split a word into WordPiece sub-tokens."""
        if word in self.vocab:
            return [word]
        tokens = []
        start = 0
        while start < len(word):
            end = len(word)
            found = None
            while start < end:
                substr = word[start:end]
                if start > 0:
                    substr = "##" + substr
                if substr in self.vocab:
                    found = substr
                    break
                end -= 1
            if found is None:
                tokens.append(self.UNK_TOKEN)
                start += 1
            else:
                tokens.append(found)
                start = end
        return tokens

    def encode(self, text):
        """Tokenize text and return (input_ids, attention_mask) as lists.

        Adds [CLS] and [SEP] tokens. Truncates to max_length.
        Pads to max_length with [PAD] tokens.
        """
        words = self._basic_tokenize(text)
        wp_tokens = []
        for word in words:
            wp_tokens.extend(self._wordpiece_tokenize(word))

        # Truncate (account for [CLS] and [SEP])
        max_wp = self.max_length - 2
        if len(wp_tokens) > max_wp:
            wp_tokens = wp_tokens[:max_wp]

        # Build input_ids: [CLS] + tokens + [SEP]
        input_ids = [self.cls_id]
        for token in wp_tokens:
            input_ids.append(self.vocab.get(token, self.unk_id))
        input_ids.append(self.sep_id)

        # Attention mask: 1 for real tokens, 0 for padding
        attention_mask = [1] * len(input_ids)

        # Pad to max_length
        pad_len = self.max_length - len(input_ids)
        input_ids.extend([self.pad_id] * pad_len)
        attention_mask.extend([0] * pad_len)

        return input_ids, attention_mask

    def encode_batch(self, texts):
        """Encode multiple texts. Returns (input_ids_batch, attention_mask_batch)."""
        all_ids = []
        all_masks = []
        for text in texts:
            ids, mask = self.encode(text)
            all_ids.append(ids)
            all_masks.append(mask)
        return all_ids, all_masks
