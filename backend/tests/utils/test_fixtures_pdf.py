"""
PDF Test Fixtures for Comprehensive Testing.

This module provides pytest fixtures for generating various types of PDF files
to test edge cases, failure scenarios, and performance characteristics.

All fixtures are designed to BREAK the PDF processing system and find bugs.
"""

import pytest
import fitz  # PyMuPDF
from pathlib import Path
from typing import Tuple


@pytest.fixture
def small_pdf_bytes() -> bytes:
    """
    Generate a small PDF (1-2 pages, ~10KB) for baseline testing.
    
    Returns:
        bytes: Valid small PDF file content
    """
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page()
    text1 = """Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that focuses on 
developing systems that can learn from and make decisions based on data.

Key concepts include:
- Supervised learning
- Unsupervised learning
- Reinforcement learning
"""
    page1.insert_text((72, 72), text1)
    
    # Page 2
    page2 = doc.new_page()
    text2 = """Applications of Machine Learning

Machine learning has numerous applications across various industries:
1. Healthcare - Disease diagnosis and prediction
2. Finance - Fraud detection and risk assessment
3. E-commerce - Recommendation systems
4. Transportation - Autonomous vehicles
"""
    page2.insert_text((72, 72), text2)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def medium_pdf_bytes() -> bytes:
    """
    Generate a medium PDF (10-20 pages, ~500KB) simulating typical lecture notes.
    
    Returns:
        bytes: Valid medium-sized PDF file content
    """
    doc = fitz.open()
    
    # Generate 15 pages with varied content
    for i in range(15):
        page = doc.new_page()
        
        # Title
        title = f"Chapter {i + 1}: Advanced Topics in AI"
        page.insert_text((72, 72), title, fontsize=16)
        
        # Content - make it substantial
        content = f"""
Section {i + 1}.1: Introduction

This chapter explores advanced concepts in artificial intelligence and machine learning.
We will cover theoretical foundations, practical applications, and recent research developments.

Section {i + 1}.2: Key Concepts

The fundamental principles discussed in this chapter include:
- Neural network architectures and their evolution
- Optimization algorithms and gradient descent variants
- Regularization techniques to prevent overfitting
- Transfer learning and domain adaptation
- Ensemble methods and model combination strategies

Section {i + 1}.3: Mathematical Foundations

Let's examine the mathematical underpinnings of these concepts. The loss function
can be expressed as a combination of empirical risk and regularization terms.
The optimization process seeks to minimize this objective function through
iterative updates to the model parameters.

Section {i + 1}.4: Practical Applications

Real-world applications demonstrate the power of these techniques:
- Computer vision systems for object detection and segmentation
- Natural language processing for text understanding and generation
- Speech recognition and synthesis systems
- Recommendation engines for personalized content delivery
- Anomaly detection in cybersecurity and fraud prevention

Section {i + 1}.5: Recent Developments

The field continues to evolve rapidly with new architectures and training methods.
Recent breakthroughs include transformer models, self-supervised learning,
and few-shot learning approaches that reduce data requirements.

Section {i + 1}.6: Challenges and Future Directions

Despite significant progress, several challenges remain:
- Interpretability and explainability of complex models
- Robustness to adversarial examples and distribution shift
- Ethical considerations and bias mitigation
- Computational efficiency and environmental impact
- Data privacy and security concerns

Section {i + 1}.7: Conclusion

This chapter has provided an overview of advanced AI topics. The next chapter
will delve deeper into specific algorithms and implementation details.
"""
        page.insert_text((72, 100), content, fontsize=11)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def large_pdf_bytes() -> bytes:
    """
    Generate a large PDF (100+ pages, ~5MB) for performance testing.
    
    This fixture creates a substantial PDF to test:
    - Processing time for large documents
    - Memory usage during extraction
    - Chunking performance with large text volumes
    
    Returns:
        bytes: Valid large PDF file content
    """
    doc = fitz.open()
    
    # Generate 120 pages
    for i in range(120):
        page = doc.new_page()
        
        # Title
        title = f"Lecture {i + 1}: Deep Learning Fundamentals"
        page.insert_text((72, 50), title, fontsize=14)
        
        # Substantial content per page
        content = f"""
Lecture Overview

This lecture covers fundamental concepts in deep learning, including neural network
architectures, training algorithms, and optimization techniques. We will explore
both theoretical foundations and practical implementation considerations.

1. Introduction to Neural Networks

Neural networks are computational models inspired by biological neural systems.
They consist of interconnected nodes (neurons) organized in layers. Each connection
has an associated weight that is adjusted during training to minimize prediction errors.

The basic building block is the perceptron, which computes a weighted sum of inputs
and applies an activation function. Modern networks stack multiple layers to learn
hierarchical representations of data.

2. Activation Functions

Common activation functions include:
- Sigmoid: σ(x) = 1 / (1 + exp(-x))
- Tanh: tanh(x) = (exp(x) - exp(-x)) / (exp(x) + exp(-x))
- ReLU: f(x) = max(0, x)
- Leaky ReLU: f(x) = max(αx, x) where α is a small constant
- ELU, SELU, and other variants

Each activation function has different properties affecting gradient flow,
computational efficiency, and model expressiveness.

3. Loss Functions and Optimization

Training neural networks requires defining a loss function that measures the
discrepancy between predictions and ground truth. Common loss functions include:
- Mean Squared Error (MSE) for regression tasks
- Cross-Entropy for classification problems
- Hinge loss for support vector machines
- Custom losses for specific applications

Optimization algorithms update network weights to minimize the loss:
- Stochastic Gradient Descent (SGD)
- Momentum-based methods
- Adam, RMSprop, and adaptive learning rate algorithms
- Second-order methods like L-BFGS

4. Regularization Techniques

To prevent overfitting, we employ various regularization strategies:
- L1 and L2 weight penalties
- Dropout: randomly deactivating neurons during training
- Batch normalization: normalizing layer inputs
- Data augmentation: artificially expanding the training set
- Early stopping: halting training when validation performance degrades

5. Convolutional Neural Networks

CNNs are specialized architectures for processing grid-like data such as images.
Key components include:
- Convolutional layers: apply learnable filters to extract local features
- Pooling layers: downsample spatial dimensions
- Fully connected layers: combine features for final predictions

Popular architectures: LeNet, AlexNet, VGG, ResNet, Inception, EfficientNet

6. Recurrent Neural Networks

RNNs process sequential data by maintaining hidden states across time steps.
Variants include:
- Vanilla RNNs: simple recurrent connections
- LSTMs: long short-term memory units with gating mechanisms
- GRUs: gated recurrent units as a simplified alternative
- Bidirectional RNNs: process sequences in both directions

Applications: language modeling, machine translation, speech recognition

7. Attention Mechanisms and Transformers

Attention allows models to focus on relevant parts of the input. The transformer
architecture relies entirely on attention, eliminating recurrence. Key innovations:
- Self-attention: relating different positions in a sequence
- Multi-head attention: parallel attention mechanisms
- Positional encoding: injecting sequence order information

Transformers have revolutionized NLP with models like BERT, GPT, and T5.

8. Practical Considerations

Successful deep learning projects require careful attention to:
- Data preprocessing and normalization
- Hyperparameter tuning (learning rate, batch size, architecture)
- Hardware acceleration (GPUs, TPUs)
- Debugging and visualization tools
- Model deployment and serving infrastructure

9. Summary

This lecture introduced core deep learning concepts. Future lectures will explore
advanced topics including generative models, reinforcement learning, and meta-learning.

Page {i + 1} of 120
"""
        page.insert_text((72, 80), content, fontsize=10)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def complex_formatting_pdf_bytes() -> bytes:
    """
    Generate a PDF with complex formatting (tables, multi-column, mixed fonts).
    
    Tests text extraction with challenging layouts.
    
    Returns:
        bytes: PDF with complex formatting
    """
    doc = fitz.open()
    page = doc.new_page()
    
    # Title with different font size
    page.insert_text((72, 50), "Complex Document Layout", fontsize=18)
    
    # Multi-column simulation (two columns of text)
    left_column = """Left Column Content:

This text appears in the
left column of the page.
It should be extracted
before the right column
to maintain reading order.

Key points:
- First point
- Second point
- Third point
"""
    
    right_column = """Right Column Content:

This text appears in the
right column of the page.
It should be extracted
after the left column
to maintain reading order.

Additional notes:
- Note A
- Note B
- Note C
"""
    
    # Insert columns (left at x=72, right at x=320)
    page.insert_text((72, 100), left_column, fontsize=11)
    page.insert_text((320, 100), right_column, fontsize=11)
    
    # Table-like content (simulated with aligned text)
    table_content = """
Performance Metrics Table:

Metric          Train    Valid    Test
Accuracy        0.95     0.92     0.91
Precision       0.94     0.91     0.90
Recall          0.96     0.93     0.92
F1-Score        0.95     0.92     0.91
"""
    page.insert_text((72, 350), table_content, fontsize=10)
    
    # Mixed formatting
    page.insert_text((72, 500), "Bold-like text: ", fontsize=12)
    page.insert_text((180, 500), "IMPORTANT INFORMATION", fontsize=12)
    
    # Special characters and symbols
    special_text = """
Mathematical symbols: α β γ δ ε θ λ μ π σ ω
Greek letters: Α Β Γ Δ Ε Θ Λ Μ Π Σ Ω
Arrows: → ← ↑ ↓ ⇒ ⇐
Math: ∑ ∫ ∂ ∇ √ ∞ ≈ ≠ ≤ ≥
"""
    page.insert_text((72, 550), special_text, fontsize=10)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def corrupted_pdf_bytes() -> bytes:
    """
    Generate a corrupted PDF with valid magic bytes but malformed content.
    
    This should trigger validation errors during processing.
    
    Returns:
        bytes: Corrupted PDF data
    """
    # Start with valid PDF header
    corrupted = b"%PDF-1.4\n"
    
    # Add some valid-looking but incomplete PDF structure
    corrupted += b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    
    # Add garbage data that will cause parsing errors
    corrupted += b"corrupted data " * 200
    corrupted += b"\ngarbage\n" * 100
    corrupted += b"\x00\x01\x02\x03\x04\x05" * 50
    
    # Add incomplete trailer
    corrupted += b"\ntrailer\n<< /Size 1 >>\n"
    
    return corrupted


@pytest.fixture
def password_protected_pdf_bytes(tmp_path) -> bytes:
    """
    Generate a password-protected PDF.
    
    This should be rejected during validation.
    
    Args:
        tmp_path: Pytest temporary directory fixture
        
    Returns:
        bytes: Encrypted PDF data
    """
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is password-protected content.")
    
    # Save with encryption
    temp_file = tmp_path / "encrypted.pdf"
    
    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY
        | fitz.PDF_PERM_PRINT
        | fitz.PDF_PERM_COPY
        | fitz.PDF_PERM_ANNOTATE
    )
    
    doc.save(
        str(temp_file),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner_password",
        user_pw="user_password",
        permissions=perm,
    )
    doc.close()
    
    # Read encrypted PDF
    encrypted_bytes = temp_file.read_bytes()
    
    return encrypted_bytes


@pytest.fixture
def empty_pdf_bytes() -> bytes:
    """
    Generate a PDF with blank pages (no extractable text).
    
    This should trigger "no text extracted" errors.
    
    Returns:
        bytes: PDF with empty pages
    """
    doc = fitz.open()
    
    # Create 3 blank pages with no text
    for _ in range(3):
        doc.new_page()
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def image_only_pdf_bytes() -> bytes:
    """
    Generate a PDF with only images (no extractable text).
    
    Simulates scanned documents or image-based PDFs.
    
    Returns:
        bytes: PDF containing only images
    """
    doc = fitz.open()
    page = doc.new_page()
    
    # Create a simple image (solid color rectangle)
    # In a real scenario, this would be an actual image
    # For testing, we just create a page with no text
    # The key is that text extraction will return empty/minimal content
    
    # Add a very small amount of metadata that might be extracted
    # but no actual readable content
    page.insert_text((72, 72), " ", fontsize=1)  # Nearly invisible
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def special_characters_pdf_bytes() -> bytes:
    """
    Generate a PDF with special characters, Unicode, emojis, and RTL text.
    
    Tests handling of various character encodings and text directions.
    
    Returns:
        bytes: PDF with special characters
    """
    doc = fitz.open()
    page = doc.new_page()
    
    content = """Special Characters Test Document

1. Unicode Characters:
   - Accented: café, naïve, résumé, Zürich
   - Symbols: © ® ™ € £ ¥ § ¶
   - Arrows: ← → ↑ ↓ ↔ ⇐ ⇒ ⇔
   - Math: ∀ ∃ ∈ ∉ ∋ ∑ ∏ √ ∞ ∫ ≈ ≠ ≤ ≥

2. Emojis and Symbols:
   - Faces: 😀 😃 😄 😁 😆 😊 🙂 🙃
   - Objects: 📚 📖 📝 ✏️ 🖊️ 📊 📈
   - Check marks: ✓ ✔ ✗ ✘

3. Greek Letters:
   - Lowercase: α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω
   - Uppercase: Α Β Γ Δ Ε Ζ Η Θ Ι Κ Λ Μ Ν Ξ Ο Π Ρ Σ Τ Υ Φ Χ Ψ Ω

4. Mathematical Notation:
   - Operators: + − × ÷ ± ∓ ⊕ ⊗ ⊙
   - Relations: = ≠ < > ≤ ≥ ≈ ≡ ∝ ∼
   - Sets: ∅ ∈ ∉ ⊂ ⊃ ⊆ ⊇ ∪ ∩
   - Logic: ∀ ∃ ∧ ∨ ¬ ⇒ ⇔

5. Superscripts and Subscripts:
   - x² + y² = z²
   - H₂O, CO₂, CH₄
   - E = mc²

6. Mixed Languages:
   - English: Hello World
   - Spanish: Hola Mundo
   - French: Bonjour le monde
   - German: Hallo Welt
   - Russian: Привет мир
   - Chinese: 你好世界
   - Japanese: こんにちは世界
   - Korean: 안녕하세요 세계
   - Arabic: مرحبا بالعالم
   - Hebrew: שלום עולם

7. Special Punctuation:
   - Quotes: "double" 'single' „German" «French»
   - Dashes: - – — ―
   - Ellipsis: … (three dots)
   - Bullets: • ‣ ⁃ ◦

8. Zero-Width and Combining Characters:
   - Combining diacritics: e + ́ = é
   - Zero-width space: word​word (invisible space)
   - Zero-width joiner: ‍

9. Unusual Whitespace:
   - Non-breaking space: word word
   - Em space: word word
   - Thin space: word word

10. Control Characters and Edge Cases:
    - Tab:	separated	values
    - Newline preservation test
    - Multiple     spaces     test
"""
    
    page.insert_text((72, 50), content, fontsize=10)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def oversized_pdf_50mb_exact() -> bytes:
    """
    Generate a PDF exactly at the 50MB size limit.
    
    This should PASS validation (at the boundary).
    
    Returns:
        bytes: PDF exactly 50MB in size
    """
    doc = fitz.open()
    
    # Generate pages until we reach approximately 50MB
    target_size = 50 * 1024 * 1024  # 50MB
    current_size = 0
    page_num = 0
    
    # Create a template text that's substantial
    template_text = "A" * 5000 + "\n" + "B" * 5000 + "\n" + "C" * 5000
    
    while current_size < target_size - 100000:  # Leave room for PDF overhead
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {page_num}\n{template_text}", fontsize=10)
        page_num += 1
        
        # Check current size
        current_bytes = doc.tobytes()
        current_size = len(current_bytes)
        
        # Safety limit to prevent infinite loop
        if page_num > 5000:
            break
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def oversized_pdf_51mb() -> bytes:
    """
    Generate a PDF just over the 50MB size limit (51MB).
    
    This should FAIL validation.
    
    Returns:
        bytes: PDF over 50MB in size
    """
    doc = fitz.open()
    
    # Generate pages until we exceed 50MB
    target_size = 51 * 1024 * 1024  # 51MB
    current_size = 0
    page_num = 0
    
    # Create a template text that's substantial
    template_text = "X" * 5000 + "\n" + "Y" * 5000 + "\n" + "Z" * 5000
    
    while current_size < target_size - 100000:
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {page_num}\n{template_text}", fontsize=10)
        page_num += 1
        
        # Check current size
        current_bytes = doc.tobytes()
        current_size = len(current_bytes)
        
        # Safety limit
        if page_num > 5000:
            break
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def fake_pdf_wrong_magic_bytes() -> bytes:
    """
    Generate a non-PDF file with .pdf extension but wrong magic bytes.
    
    This should FAIL magic bytes validation.
    
    Returns:
        bytes: Non-PDF data (PNG magic bytes)
    """
    # PNG magic bytes
    fake_pdf = b"\x89PNG\r\n\x1a\n"
    
    # Add some fake content
    fake_pdf += b"This is actually a PNG file, not a PDF!" * 100
    
    return fake_pdf


@pytest.fixture
def pdf_with_long_sentences() -> bytes:
    """
    Generate a PDF with extremely long sentences (>2000 tokens).
    
    Tests chunking behavior with sentences that exceed chunk size.
    
    Returns:
        bytes: PDF with very long sentences
    """
    doc = fitz.open()
    page = doc.new_page()
    
    # Create an extremely long sentence
    long_sentence = (
        "This is an extremely long sentence that continues for a very long time "
        "and includes many clauses and subclauses and additional information "
        "that makes it exceed the typical chunk size limit and tests whether "
        "the chunking algorithm can handle sentences that are longer than the "
        "maximum chunk size and whether it will split them appropriately or "
        "handle them as a special case because in real-world documents you "
        "sometimes encounter run-on sentences or very long technical descriptions "
        "that don't have natural breaking points and the system needs to handle "
        "these gracefully without losing information or creating invalid chunks "
    ) * 50  # Repeat to make it very long
    
    page.insert_text((72, 72), long_sentence, fontsize=10)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def pdf_with_short_sentences() -> bytes:
    """
    Generate a PDF with only very short sentences (2-3 words each).
    
    Tests chunking behavior with minimal sentence length.
    
    Returns:
        bytes: PDF with very short sentences
    """
    doc = fitz.open()
    page = doc.new_page()
    
    # Create many short sentences
    short_sentences = "\n".join([
        "AI works.",
        "Models learn.",
        "Data matters.",
        "Training helps.",
        "Testing validates.",
        "Accuracy improves.",
        "Errors decrease.",
        "Performance grows.",
        "Systems adapt.",
        "Results vary.",
    ] * 100)  # Repeat many times
    
    page.insert_text((72, 72), short_sentences, fontsize=10)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


@pytest.fixture
def pdf_only_whitespace() -> bytes:
    """
    Generate a PDF with only whitespace characters.
    
    Tests handling of PDFs with no meaningful content.
    
    Returns:
        bytes: PDF with only whitespace
    """
    doc = fitz.open()
    page = doc.new_page()
    
    # Insert only whitespace
    whitespace_content = " " * 1000 + "\n" * 100 + "\t" * 100
    page.insert_text((72, 72), whitespace_content, fontsize=10)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes
