import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatINR, analyzeKhataPhoto, confirmScanEntries } from '../services/api';
import { useApp } from '../context/AppContext';
import './ScanBook.css';

const ScanBook = () => {
  const navigate = useNavigate();
  const { incrementRefresh } = useApp();

  // Mode: 'upload' | 'edit' | 'analyzing' | 'review' | 'success'
  const [mode, setMode] = useState('upload');

  // Drag-and-drop state
  const [isDragging, setIsDragging] = useState(false);

  // Raw Uploaded Image
  const [originalImageBitmap, setOriginalImageBitmap] = useState(null);

  // Edit Controls
  const canvasRef = useRef(null);
  const [rotationAngle, setRotationAngle] = useState(0); // 0, 90, 180, 270
  const [brightness, setBrightness] = useState(100); // 50 - 150%
  const [contrast, setContrast] = useState(100); // 50 - 200%
  const [bwFilter, setBwFilter] = useState(false); // High-contrast B&W threshold
  const [cropPreset, setCropPreset] = useState('full'); // 'full' | 'top' | 'bottom' | 'center'

  // Analysis & Review State
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);
  const [extractedEntries, setExtractedEntries] = useState([]);
  const [saveResult, setSaveResult] = useState(null);
  const [savingLedger, setSavingLedger] = useState(false);

  // File Upload Handlers
  const handleFile = (file) => {
    if (!file || !file.type.startsWith('image/')) {
      alert('Please select a valid image file (JPEG, PNG, WEBP).');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      loadImageIntoEditor(event.target.result);
    };
    reader.readAsDataURL(file);
  };

  const handleInputChange = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) {
      handleFile(file);
    }
  };

  // Drag and Drop
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  // Paste image from clipboard support (Ctrl+V)
  useEffect(() => {
    const handlePaste = (e) => {
      if (mode !== 'upload') return;
      if (e.clipboardData && e.clipboardData.files.length > 0) {
        const item = e.clipboardData.files[0];
        if (item.type.startsWith('image/')) {
          handleFile(item);
        }
      }
    };
    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // Helper: Load an image DataURL into the Editor Canvas
  const loadImageIntoEditor = (dataUrl) => {
    setRotationAngle(0);
    setBrightness(100);
    setContrast(100);
    setBwFilter(false);
    setCropPreset('full');
    setAnalysisError(null);

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      setOriginalImageBitmap(img);
      setMode('edit');
    };
    img.src = dataUrl;
  };

  // Render Edits (Rotate, Brightness, Contrast, B&W, Crop) onto Canvas
  const renderEditedCanvas = useCallback(() => {
    if (!originalImageBitmap || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = originalImageBitmap;

    // Calculate crop rectangle
    let sx = 0, sy = 0, sWidth = img.width, sHeight = img.height;
    if (cropPreset === 'top') {
      sHeight = img.height * 0.55;
    } else if (cropPreset === 'bottom') {
      sy = img.height * 0.45;
      sHeight = img.height * 0.55;
    } else if (cropPreset === 'center') {
      sx = img.width * 0.1;
      sy = img.height * 0.15;
      sWidth = img.width * 0.8;
      sHeight = img.height * 0.7;
    }

    // Determine dimensions considering rotation
    const isSideways = rotationAngle === 90 || rotationAngle === 270;
    canvas.width = isSideways ? sHeight : sWidth;
    canvas.height = isSideways ? sWidth : sHeight;

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Apply rotation around center
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate((rotationAngle * Math.PI) / 180);

    // Apply filters (Brightness & Contrast)
    ctx.filter = `brightness(${brightness}%) contrast(${contrast}%)`;

    // Draw cropped portion
    ctx.drawImage(
      img,
      sx, sy, sWidth, sHeight,
      -sWidth / 2, -sHeight / 2, sWidth, sHeight
    );
    ctx.restore();

    // High-contrast B&W Binarization threshold filter for handwritten documents
    if (bwFilter) {
      const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const data = imgData.data;
      const threshold = 135;
      for (let i = 0; i < data.length; i += 4) {
        const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        const val = gray > threshold ? 255 : 20;
        data[i] = val;
        data[i + 1] = val;
        data[i + 2] = val;
      }
      ctx.putImageData(imgData, 0, 0);
    }
  }, [originalImageBitmap, rotationAngle, brightness, contrast, bwFilter, cropPreset]);

  useEffect(() => {
    if (mode === 'edit') {
      renderEditedCanvas();
    }
  }, [mode, renderEditedCanvas]);

  // Rotate 90 degrees
  const handleRotate = (delta) => {
    setRotationAngle((prev) => (prev + delta + 360) % 360);
  };

  // Reset image adjustments
  const handleResetAdjustments = () => {
    setBrightness(100);
    setContrast(100);
    setBwFilter(false);
    setCropPreset('full');
    setRotationAngle(0);
  };

  // Reset to Upload view
  const handleResetToUpload = () => {
    setMode('upload');
    setOriginalImageBitmap(null);
    setExtractedEntries([]);
    setAnalysisError(null);
  };

  // Analyze Image & Extract Khata Ledger Data
  const handleAnalyzePhoto = async () => {
    if (!canvasRef.current) return;
    setAnalyzing(true);
    setAnalysisError(null);

    try {
      const processedDataUrl = canvasRef.current.toDataURL('image/jpeg', 0.92);
      const res = await analyzeKhataPhoto(processedDataUrl, 1);

      if (res && res.entries && res.entries.length > 0) {
        setExtractedEntries(res.entries);
        setMode('review');
      } else {
        setAnalysisError('No clear Khata ledger transactions detected in this photo. Try adjusting brightness/contrast or crop the ledger area.');
      }
    } catch (err) {
      console.error('Scan analysis error:', err);
      setAnalysisError('Failed to analyze photograph. Please verify connectivity or try again.');
    } finally {
      setAnalyzing(false);
    }
  };

  // Demo Khata Notebook Test Helper
  const handleLoadSampleLedger = () => {
    const sampleCanvas = document.createElement('canvas');
    sampleCanvas.width = 800;
    sampleCanvas.height = 1000;
    const ctx = sampleCanvas.getContext('2d');

    // Paper background with ruled lines
    ctx.fillStyle = '#fdfbf7';
    ctx.fillRect(0, 0, 800, 1000);

    // Notebook margin and ruled lines
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1.5;
    for (let y = 100; y < 960; y += 45) {
      ctx.beginPath();
      ctx.moveTo(40, y);
      ctx.lineTo(760, y);
      ctx.stroke();
    }

    // Red vertical ledger margin line
    ctx.strokeStyle = '#fca5a5';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(180, 60);
    ctx.lineTo(180, 960);
    ctx.stroke();

    // Handwritten Title
    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 26px serif';
    ctx.fillText('ಶ್ರೀ ಮಂಜುನಾಥ ಪ್ರಾವಿಷನ್ ಸ್ಟೋರ್ - ಖಾತಾ ಬುಕ್', 190, 85);

    // Entries in Indian Kirana ledger format
    ctx.font = 'bold 22px sans-serif';
    ctx.fillStyle = '#0f172a';

    // Entry 1: Existing customer Suresh Kumar (Credit ₹450)
    ctx.fillText('1. Suresh Kumar', 190, 180);
    ctx.font = '18px sans-serif';
    ctx.fillStyle = '#475569';
    ctx.fillText('Atta 5kg, Sugar 2kg', 190, 215);
    ctx.font = 'bold 22px sans-serif';
    ctx.fillStyle = '#dc2626';
    ctx.fillText('₹ 450 (ಉಧಾರ/Credit)', 520, 180);

    // Entry 2: Existing customer Govind (Payment ₹500)
    ctx.font = 'bold 22px sans-serif';
    ctx.fillStyle = '#0f172a';
    ctx.fillText('2. Govind', 190, 310);
    ctx.font = '18px sans-serif';
    ctx.fillStyle = '#475569';
    ctx.fillText('Gpay / Cash Payment', 190, 345);
    ctx.font = 'bold 22px sans-serif';
    ctx.fillStyle = '#16a34a';
    ctx.fillText('₹ 500 (ಜಮಾ/Paid)', 520, 310);

    // Entry 3: New customer Kiran Rao (Credit ₹280)
    ctx.font = 'bold 22px sans-serif';
    ctx.fillStyle = '#0f172a';
    ctx.fillText('3. Kiran Rao (New)', 190, 440);
    ctx.font = '18px sans-serif';
    ctx.fillStyle = '#475569';
    ctx.fillText('Basmati Rice 2kg, Salt 1 pkt', 190, 475);
    ctx.font = 'bold 22px sans-serif';
    ctx.fillStyle = '#dc2626';
    ctx.fillText('₹ 280 (Credit)', 520, 440);

    const sampleUrl = sampleCanvas.toDataURL('image/jpeg', 0.95);
    loadImageIntoEditor(sampleUrl);
  };

  // Review Entries State Management
  const handleUpdateEntry = (index, field, value) => {
    setExtractedEntries((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const handleRemoveEntry = (index) => {
    setExtractedEntries((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleAddManualEntry = () => {
    const newEntry = {
      temp_id: `manual-${Date.now()}`,
      customer_name: '',
      extracted_name: '',
      matched_customer_id: null,
      matched_customer_name: null,
      is_new_customer: true,
      amount: 100,
      type: 'CREDIT',
      notes: 'Grocery items',
      date: 'Today',
    };
    setExtractedEntries((prev) => [...prev, newEntry]);
  };

  // Save Approved Entries into Database
  const handleConfirmAndSave = async () => {
    if (extractedEntries.length === 0) return;
    setSavingLedger(true);

    try {
      const res = await confirmScanEntries(extractedEntries, 1);
      setSaveResult(res);
      setMode('success');
      incrementRefresh();
      if (typeof window !== 'undefined' && window.dispatchEvent) {
        window.dispatchEvent(new CustomEvent('dukaanai:refresh'));
      }
    } catch (err) {
      console.error('Failed to save scanned ledger:', err);
      alert('Failed to save scanned entries. Please check details and try again.');
    } finally {
      setSavingLedger(false);
    }
  };

  return (
    <div className="scan-book-page animate-fadeIn">
      {/* Page Header */}
      <div className="scan-header">
        <div className="scan-header-text">
          <div className="flex items-center gap-2">
            <span className="page-icon">🖼️</span>
            <h1 className="page-title">Upload Khata Book</h1>
            <span className="live-ocr-badge">AI Vision Ledger</span>
          </div>
          <p className="page-subtitle">
            Upload a photograph of your handwritten or printed Khata diary from your gallery to automatically extract and record transactions
          </p>
        </div>

        <div className="scan-header-actions">
          {mode !== 'upload' && (
            <button
              type="button"
              className="btn-scan-secondary"
              onClick={handleResetToUpload}
              title="Upload another photo from gallery"
            >
              🔄 Upload Another
            </button>
          )}
          <button
            type="button"
            className="btn-sample-khata"
            onClick={handleLoadSampleLedger}
            title="Load an instant sample Khata notebook page to test scanning"
          >
            📋 Load Demo Khata Page
          </button>
        </div>
      </div>

      {/* STEP 1: PURE GALLERY UPLOAD LANDING VIEW */}
      {mode === 'upload' && (
        <div className="gallery-upload-view animate-fadeIn">
          <div
            className={`gallery-dropzone-hero ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              type="file"
              id="gallery-input-main"
              accept="image/*"
              onChange={handleInputChange}
              className="hidden-file-input"
            />

            <div className="dropzone-hero-content">
              <div className="dropzone-hero-icon">
                <span>📁</span>
              </div>

              <h2 className="dropzone-hero-title">
                Choose Khata Photograph from Gallery
              </h2>

              <p className="dropzone-hero-subtitle">
                Select any photo of your handwritten notebook, diary, Kirana bill, or receipt.
                <br />
                You can drag & drop, browse your files, or press <strong>Ctrl+V</strong> to paste.
              </p>

              <div className="dropzone-actions-group">
                <label htmlFor="gallery-input-main" className="btn-browse-gallery">
                  <span className="btn-icon">🖼️</span>
                  <span>Browse Saved Gallery / Files</span>
                </label>

                <button
                  type="button"
                  className="btn-quick-demo"
                  onClick={handleLoadSampleLedger}
                >
                  <span className="btn-icon">📋</span>
                  <span>Try Demo Khata Sheet</span>
                </button>
              </div>

              <div className="supported-formats-pill">
                Supports JPG, PNG, WEBP, HEIC • Auto-enhancement & Crop available
              </div>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2: IMAGE PREVIEW, CROP, ROTATE, & ADJUSTMENTS */}
      {(mode === 'edit' || mode === 'analyzing') && (
        <div className="image-editor-section animate-fadeIn">
          <div className="editor-layout">
            {/* Canvas Preview Area */}
            <div className="canvas-preview-card">
              <div className="preview-header">
                <span className="preview-title">Khata Image Preview & Adjustments</span>
                <div className="preview-badges">
                  <span className="badge-rotation">Angle: {rotationAngle}°</span>
                  {bwFilter && <span className="badge-bw">High-Contrast B&W Active</span>}
                </div>
              </div>

              <div className="canvas-stage-wrapper">
                <canvas ref={canvasRef} className="editor-canvas" />

                {/* Laser Scanning Animation Overlay */}
                {analyzing && (
                  <div className="scanner-beam-overlay">
                    <div className="scanner-laser-line" />
                    <div className="scanner-glow-text">
                      ✨ Analyzing ledger with AI Vision...
                    </div>
                  </div>
                )}
              </div>

              {analysisError && (
                <div className="analysis-error-banner animate-slideUp">
                  ⚠️ {analysisError}
                </div>
              )}
            </div>

            {/* Editing Tools Sidebar */}
            <div className="editor-tools-sidebar">
              {/* Tool 1: Rotate */}
              <div className="tool-card">
                <h4 className="tool-title">🔄 Rotate</h4>
                <div className="tool-btn-group">
                  <button
                    type="button"
                    className="tool-btn"
                    onClick={() => handleRotate(-90)}
                    disabled={analyzing}
                  >
                    ↺ 90° Left
                  </button>
                  <button
                    type="button"
                    className="tool-btn"
                    onClick={() => handleRotate(90)}
                    disabled={analyzing}
                  >
                    ↻ 90° Right
                  </button>
                </div>
              </div>

              {/* Tool 2: Crop Preset */}
              <div className="tool-card">
                <h4 className="tool-title">✂️ Crop Area</h4>
                <div className="crop-presets-grid">
                  <button
                    type="button"
                    className={`crop-pill ${cropPreset === 'full' ? 'active' : ''}`}
                    onClick={() => setCropPreset('full')}
                    disabled={analyzing}
                  >
                    Full Page
                  </button>
                  <button
                    type="button"
                    className={`crop-pill ${cropPreset === 'top' ? 'active' : ''}`}
                    onClick={() => setCropPreset('top')}
                    disabled={analyzing}
                  >
                    Top Half
                  </button>
                  <button
                    type="button"
                    className={`crop-pill ${cropPreset === 'bottom' ? 'active' : ''}`}
                    onClick={() => setCropPreset('bottom')}
                    disabled={analyzing}
                  >
                    Bottom Half
                  </button>
                  <button
                    type="button"
                    className={`crop-pill ${cropPreset === 'center' ? 'active' : ''}`}
                    onClick={() => setCropPreset('center')}
                    disabled={analyzing}
                  >
                    Center Box
                  </button>
                </div>
              </div>

              {/* Tool 3: Image Adjustments */}
              <div className="tool-card">
                <h4 className="tool-title">🎛️ Image Adjustments</h4>

                <div className="slider-control">
                  <div className="slider-label-row">
                    <span>Brightness</span>
                    <span className="slider-val">{brightness}%</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="150"
                    value={brightness}
                    onChange={(e) => setBrightness(Number(e.target.value))}
                    disabled={analyzing}
                  />
                </div>

                <div className="slider-control mt-3">
                  <div className="slider-label-row">
                    <span>Contrast</span>
                    <span className="slider-val">{contrast}%</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="200"
                    value={contrast}
                    onChange={(e) => setContrast(Number(e.target.value))}
                    disabled={analyzing}
                  />
                </div>

                <label className="checkbox-control mt-3">
                  <input
                    type="checkbox"
                    checked={bwFilter}
                    onChange={(e) => setBwFilter(e.target.checked)}
                    disabled={analyzing}
                  />
                  <span>Document Scanner B&W (Enhance Ink)</span>
                </label>

                <button
                  type="button"
                  className="btn-reset-adjustments mt-3"
                  onClick={handleResetAdjustments}
                  disabled={analyzing}
                >
                  Reset Adjustments
                </button>
              </div>

              {/* Primary Analyze Action */}
              <div className="editor-cta-box">
                <button
                  type="button"
                  className="btn-analyze-khata"
                  onClick={handleAnalyzePhoto}
                  disabled={analyzing}
                >
                  {analyzing ? '⏳ Analyzing Photo...' : '✨ Analyze Khata Book'}
                </button>

                <button
                  type="button"
                  className="btn-retake"
                  onClick={handleResetToUpload}
                  disabled={analyzing}
                >
                  Choose Another Photo
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* STEP 3: REVIEW EXTRACTED TRANSACTIONS & CUSTOMER MATCHING */}
      {mode === 'review' && (
        <div className="review-section-container animate-slideUp">
          <div className="review-header-bar">
            <div>
              <h2 className="review-title">
                Khata Verification & Profile Matching ({extractedEntries.length} Entries)
              </h2>
              <p className="review-subtitle">
                Review parsed ledger transactions. Existing customer balances will update directly; new customers will receive new profiles.
              </p>
            </div>

            <div className="review-header-buttons">
              <button
                type="button"
                className="btn-add-entry"
                onClick={handleAddManualEntry}
              >
                ➕ Add Another Line
              </button>
              <button
                type="button"
                className="btn-confirm-all"
                onClick={handleConfirmAndSave}
                disabled={savingLedger || extractedEntries.length === 0}
              >
                {savingLedger ? 'Saving to Khata...' : '💾 Confirm & Save All to Khata'}
              </button>
            </div>
          </div>

          {/* Entries Cards List */}
          <div className="entries-review-grid">
            {extractedEntries.map((entry, idx) => (
              <div
                key={entry.temp_id || idx}
                className={`entry-card ${entry.is_new_customer ? 'is-new-profile' : 'is-existing-profile'}`}
              >
                {/* Card Header with Customer Profile Match Status & Actions */}
                <div className="entry-card-header">
                  <div className="profile-match-badge">
                    {entry.is_new_customer ? (
                      <span className="badge-new-customer">
                        🔵 New Person (Will Create Account)
                      </span>
                    ) : (
                      <span className="badge-existing-customer">
                        🟢 Existing Profile: {entry.matched_customer_name} (ID #{entry.matched_customer_id})
                      </span>
                    )}
                  </div>

                  <button
                    type="button"
                    className="entry-delete-btn"
                    onClick={() => handleRemoveEntry(idx)}
                    title="Remove this entry"
                  >
                    ✕ Remove
                  </button>
                </div>

                {/* Row 1: Customer Name */}
                <div className="entry-field-block">
                  <label className="entry-field-label">Customer Name</label>
                  <input
                    type="text"
                    className="entry-input text-bold"
                    value={entry.customer_name}
                    onChange={(e) => handleUpdateEntry(idx, 'customer_name', e.target.value)}
                    placeholder="e.g. Suresh Kumar"
                    required
                  />
                </div>

                {/* Row 2: Type Toggle & Amount */}
                <div className="entry-dual-row">
                  {/* Transaction Type Segmented Toggle */}
                  <div className="entry-field-block flex-2">
                    <label className="entry-field-label">Transaction Type</label>
                    <div className="type-toggle-bar">
                      <button
                        type="button"
                        className={`type-toggle-btn credit ${entry.type === 'CREDIT' ? 'active' : ''}`}
                        onClick={() => handleUpdateEntry(idx, 'type', 'CREDIT')}
                      >
                        <span className="type-dot red" />
                        <span>Credit (उधार / ಸಾಲ)</span>
                      </button>
                      <button
                        type="button"
                        className={`type-toggle-btn payment ${entry.type === 'PAYMENT' ? 'active' : ''}`}
                        onClick={() => handleUpdateEntry(idx, 'type', 'PAYMENT')}
                      >
                        <span className="type-dot green" />
                        <span>Payment (जमा / ಪಾವತಿ)</span>
                      </button>
                    </div>
                  </div>

                  {/* Amount with Rupee Prefix */}
                  <div className="entry-field-block flex-1">
                    <label className="entry-field-label">Amount (₹)</label>
                    <div className="amount-input-wrap">
                      <span className="amount-symbol">₹</span>
                      <input
                        type="number"
                        step="1"
                        min="1"
                        className="entry-input amount-val-input"
                        value={entry.amount}
                        onChange={(e) => handleUpdateEntry(idx, 'amount', Number(e.target.value))}
                        placeholder="0"
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* Row 3: Items / Notes */}
                <div className="entry-field-block">
                  <label className="entry-field-label">Items / Description</label>
                  <input
                    type="text"
                    className="entry-input"
                    value={entry.notes || ''}
                    onChange={(e) => handleUpdateEntry(idx, 'notes', e.target.value)}
                    placeholder="e.g. Atta 5kg, Sugar 1kg"
                  />
                </div>

                {/* Account Impact Notice */}
                <div className={`entry-impact-box ${entry.is_new_customer ? 'impact-new' : 'impact-existing'}`}>
                  {!entry.is_new_customer ? (
                    <span>
                      ℹ️ Existing Account: Current Balance <strong>{formatINR(entry.current_balance || 0)}</strong> →{' '}
                      Will record <strong>{entry.type === 'CREDIT' ? `+${formatINR(entry.amount)} Credit` : `-${formatINR(entry.amount)} Payment`}</strong>
                    </span>
                  ) : (
                    <span>
                      ✨ New Account: Will create profile for <strong>{entry.customer_name || 'this customer'}</strong> with {formatINR(entry.amount)} opening balance.
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="review-bottom-actions">
            <button
              type="button"
              className="btn-scan-secondary"
              onClick={() => setMode('edit')}
            >
              ← Back to Image
            </button>

            <button
              type="button"
              className="btn-confirm-all large-cta"
              onClick={handleConfirmAndSave}
              disabled={savingLedger || extractedEntries.length === 0}
            >
              {savingLedger ? 'Saving to Khata...' : '💾 Confirm & Save All to Khata'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: SUCCESS CONFIRMATION SCREEN */}
      {mode === 'success' && saveResult && (
        <div className="success-screen animate-fadeIn">
          <div className="success-card">
            <div className="success-icon-badge">🎉</div>
            <h2 className="success-title">Khata Book Scanned & Recorded!</h2>
            <p className="success-subtitle">
              All transactions have been successfully recorded in the digital ledger.
            </p>

            <div className="success-stats-grid">
              <div className="stat-card">
                <span className="stat-num">{saveResult.processed_count || 0}</span>
                <span className="stat-lbl">Entries Saved</span>
              </div>
              <div className="stat-card">
                <span className="stat-num updated">{saveResult.existing_customers_updated || 0}</span>
                <span className="stat-lbl">Existing Profiles Updated</span>
              </div>
              <div className="stat-card">
                <span className="stat-num created">{saveResult.new_customers_created || 0}</span>
                <span className="stat-lbl">New Profiles Created</span>
              </div>
            </div>

            <div className="success-nav-actions">
              <button
                type="button"
                className="btn-nav-action"
                onClick={() => navigate('/transactions')}
              >
                📋 View in Transactions
              </button>
              <button
                type="button"
                className="btn-nav-action"
                onClick={() => navigate('/customers')}
              >
                👥 View in Customers
              </button>
              <button
                type="button"
                className="btn-nav-action primary"
                onClick={handleResetToUpload}
              >
                🖼️ Upload Another Photo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScanBook;
