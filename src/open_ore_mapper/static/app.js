(function () {
  'use strict';

  var fileInput = document.getElementById('file-input');
  var sensorInput = document.getElementById('sensor-input');
  var wavelengthsInput = document.getElementById('wavelengths-input');
  var excludedBandsInput = document.getElementById('excluded-bands-input');
  var minBandFractionInput = document.getElementById('min-band-fraction-input');
  var runQcBtn = document.getElementById('run-qc-btn');
  var runPredictBtn = document.getElementById('run-predict-btn');
  var statusBar = document.getElementById('status-bar');
  var resultsEmpty = document.getElementById('results-empty');
  var resultsLoading = document.getElementById('results-loading');
  var resultsError = document.getElementById('results-error');
  var errorMessage = document.getElementById('error-message');
  var resultsContent = document.getElementById('results-content');
  var qcSection = document.getElementById('qc-section');
  var predictionSection = document.getElementById('prediction-section');
  var qcStatus = document.getElementById('qc-status');
  var qcRetainedBands = document.getElementById('qc-retained-bands');
  var qcExcludedBands = document.getElementById('qc-excluded-bands');
  var qcValidFraction = document.getElementById('qc-valid-fraction');
  var qcWarnings = document.getElementById('qc-warnings');
  var predictionStatistics = document.getElementById('prediction-statistics');
  var predictionLayers = document.getElementById('prediction-layers');
  var connectionStatus = document.getElementById('connection-status');

  // --- Helpers ---

  function showOnly() {
    var args = arguments;
    resultsEmpty.classList.add('hidden');
    resultsLoading.classList.add('hidden');
    resultsError.classList.add('hidden');
    resultsContent.classList.add('hidden');
    for (var i = 0; i < args.length; i++) {
      args[i].classList.remove('hidden');
    }
  }

  function setStatus(text, className) {
    statusBar.textContent = text;
    statusBar.className = 'status-bar';
    if (className) {
      statusBar.classList.add(className);
    }
  }

  function disableButtons(disabled) {
    runQcBtn.disabled = disabled;
    runPredictBtn.disabled = disabled;
  }

  function getSelectedFile() {
    return fileInput && fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;
  }

  function buildOptions() {
    var opts = {};
    opts.sensor = sensorInput ? sensorInput.value : 'cubert_ultris_s5';

    var wavelengths = wavelengthsInput ? wavelengthsInput.value.trim() : '';
    if (wavelengths) {
      try {
        opts.wavelengths = JSON.parse(wavelengths);
      } catch (e) {
        throw new Error('Custom wavelengths must be valid JSON, e.g. [450, 550, 650]');
      }
    }

    var excluded = excludedBandsInput ? excludedBandsInput.value.trim() : '';
    if (excluded) {
      opts.excluded_band_indices = excluded.split(',').map(function (s) {
        var n = parseInt(s.trim(), 10);
        if (isNaN(n)) throw new Error('Excluded band indices must be comma-separated integers');
        return n;
      });
    }

    var fraction = minBandFractionInput ? parseFloat(minBandFractionInput.value) : 0.5;
    if (!isNaN(fraction)) {
      opts.min_band_valid_fraction = fraction;
    }

    return opts;
  }

  function setQCResult(data) {
    qcSection.classList.remove('hidden');
    qcStatus.textContent = data.status || '--';
    var retained;
    if (data.retained_band_indices) {
      retained = data.retained_band_indices.length;
    } else if (data.band_count) {
      retained = data.band_count;
    } else {
      retained = '--';
    }
    qcRetainedBands.textContent = retained;
    qcExcludedBands.textContent = (data.excluded_band_indices && data.excluded_band_indices.length > 0)
      ? data.excluded_band_indices.join(', ')
      : 'none';
    qcValidFraction.textContent = data.valid_pixel_fraction != null
      ? data.valid_pixel_fraction.toFixed(4)
      : '--';
    qcWarnings.textContent = data.warnings && data.warnings.length > 0
      ? data.warnings.join('; ')
      : 'none';
  }

  function setPredictionResult(data) {
    predictionSection.classList.remove('hidden');
    predictionStatistics.textContent = '';
    if (data.statistics) {
      var dl = document.createElement('dl');
      dl.className = 'result-grid';
      var keys = Object.keys(data.statistics);
      for (var i = 0; i < keys.length; i++) {
        var key = keys[i];
        if (Object.prototype.hasOwnProperty.call(data.statistics, key)) {
          var dt = document.createElement('dt');
          dt.textContent = key;
          var dd = document.createElement('dd');
          var s = data.statistics[key];
          var parts = [];
          if (s.count != null) parts.push('Count: ' + s.count);
          if (s.percentage != null) parts.push('Percentage: ' + Number(s.percentage).toFixed(2) + '%');
          if (s.mean_confidence != null) parts.push('Mean confidence: ' + Number(s.mean_confidence).toFixed(4));
          if (s.mean_abundance != null) parts.push('Mean abundance: ' + Number(s.mean_abundance).toFixed(4));
          dd.textContent = parts.length > 0 ? parts.join(', ') : JSON.stringify(s);
          dl.appendChild(dt);
          dl.appendChild(dd);
        }
      }
      predictionStatistics.appendChild(dl);
    } else {
      var p = document.createElement('p');
      p.textContent = 'No statistics available.';
      predictionStatistics.appendChild(p);
    }

    predictionLayers.textContent = '';
    var imageFields = [
      { field: 'output_image', label: 'Class map' },
      { field: 'confidence_image', label: 'Confidence' },
      { field: 'top_abundance_image', label: 'Top abundance' },
    ];
    for (var i = 0; i < imageFields.length; i++) {
      var field = imageFields[i];
      if (data[field.field]) {
        var img = document.createElement('img');
        img.src = data[field.field];
        img.alt = field.label;
        img.setAttribute('aria-label', field.label);
        predictionLayers.appendChild(img);
      }
    }

    if (data.quality_report) {
      setQCResult(data.quality_report);
    }
  }

  // --- API calls ---

  function postForm(url, file, options) {
    var formData = new FormData();
    formData.append('file', file);
    formData.append('options', JSON.stringify(options));
    return fetch(url, { method: 'POST', body: formData });
  }

  function handleQc() {
    var file = getSelectedFile();
    if (!file) {
      setStatus('Please select a file first.', 'error');
      return;
    }

    var opts;
    try {
      opts = buildOptions();
    } catch (e) {
      setStatus(e.message, 'error');
      return;
    }

    disableButtons(true);
    showOnly(resultsLoading);
    setStatus('Running QC...', 'loading');

    postForm('/v1/qc/raster', file, opts)
      .then(function (r) {
        if (!r.ok) {
          return r.json().then(function (j) {
            throw new Error((j.error && j.error.message) || 'QC request failed');
          });
        }
        return r.json();
      })
      .then(function (data) {
        showOnly(resultsContent);
        qcSection.classList.remove('hidden');
        predictionSection.classList.add('hidden');
        setQCResult(data);
        setStatus('QC complete.', 'success');
      })
      .catch(function (err) {
        showOnly(resultsError);
        errorMessage.textContent = err.message;
        setStatus('QC failed.', 'error');
      })
      .finally(function () {
        disableButtons(false);
      });
  }

  function handlePredict() {
    var file = getSelectedFile();
    if (!file) {
      setStatus('Please select a file first.', 'error');
      return;
    }

    var opts;
    try {
      opts = buildOptions();
    } catch (e) {
      setStatus(e.message, 'error');
      return;
    }

    disableButtons(true);
    showOnly(resultsLoading);
    setStatus('Running mapping...', 'loading');

    postForm('/v1/predict', file, opts)
      .then(function (r) {
        if (!r.ok) {
          return r.json().then(function (j) {
            throw new Error((j.error && j.error.message) || 'Prediction request failed');
          });
        }
        return r.json();
      })
      .then(function (data) {
        showOnly(resultsContent);
        setQCResult(data.quality_report || {});
        setPredictionResult(data);
        setStatus('Mapping complete.', 'success');
      })
      .catch(function (err) {
        showOnly(resultsError);
        errorMessage.textContent = err.message;
        setStatus('Mapping failed.', 'error');
      })
      .finally(function () {
        disableButtons(false);
      });
  }

  // --- Event binding ---

  runQcBtn.addEventListener('click', handleQc);
  runPredictBtn.addEventListener('click', handlePredict);

  // --- Sensor toggle ---
  if (sensorInput) {
    sensorInput.addEventListener('change', function () {
      if (sensorInput.value === 'custom') {
        wavelengthsInput.disabled = false;
        wavelengthsInput.required = false;
        wavelengthsInput.setAttribute('aria-required', 'false');
      } else {
        wavelengthsInput.disabled = true;
        wavelengthsInput.required = false;
        wavelengthsInput.setAttribute('aria-required', 'false');
        wavelengthsInput.value = '';
      }
    });
    sensorInput.dispatchEvent(new Event('change'));
  }

  // --- Health check on load ---
  fetch('/health')
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.status === 'healthy') {
        connectionStatus.textContent = 'Server connected';
        connectionStatus.style.color = '#ffffff';
        connectionStatus.style.background = 'rgba(92, 184, 92, 0.35)';
        connectionStatus.style.borderColor = '#5cb85c';
      }
    })
    .catch(function () {
      connectionStatus.textContent = 'Server unreachable';
      connectionStatus.style.color = '#ffffff';
      connectionStatus.style.background = 'rgba(217, 83, 79, 0.35)';
      connectionStatus.style.borderColor = '#d9534f';
    });
})();
