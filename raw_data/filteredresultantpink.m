% Clear workspace and close all figures
clc;
clear all;
close all;

% Parameters
fs = 100;              % Sampling frequency (Hz)
duration = 12;         % Duration of the signal (seconds)
f_low = 0.1;           % Lower cutoff frequency (Hz)
f_high = 45;           % Upper cutoff frequency (Hz)
amplitude_range_Y = [-8.84, 8.84]; % Amplitude range for Y
amplitude_range_X = [-5, 5];   % Amplitude range for X

% Generate pink noise for Y
n = fs * duration;     % Number of samples
white_noise_Y = randn(1, n); % Generate white noise
b = [1 -0.99];         % First-order high-pass filter
pink_noise_Y = filter(1, b, white_noise_Y); % Apply filter to approximate pink noise

% % Apply bandpass filter for Y
% [b_band, a_band] = butter(2, [f_low f_high]/(fs/2), 'bandpass');
% pink_band_noise_Y = filter(b_band, a_band, pink_noise_Y);

% Normalize amplitude for Y
pink_band_noise_Y = pink_noise_Y / max(abs(pink_noise_Y)) * amplitude_range_Y(2);

% Plot Y signal
figure;
subplot(3,1,1);
plot(pink_band_noise_Y);
title('Filtered Pink Noise Y');
xlabel('Samples');
ylabel('Amplitude');

% Generate pink noise for X
white_noise_X = randn(1, n); % Generate white noise
pink_noise_X = filter(1, b, white_noise_X); % Apply filter to approximate pink noise

% % Apply bandpass filter for X
% pink_band_noise_X = filter(b_band, a_band, pink_noise_X);

% Normalize amplitude for X
pink_band_noise_X = pink_noise_X / max(abs(pink_noise_X)) * amplitude_range_X(2);

% Plot X signal
subplot(3,1,2);
plot(pink_band_noise_X);
title('Filtered Pink Noise X');
xlabel('Samples');
ylabel('Amplitude');

% Compute resultant signal
resultant_noise = sqrt(pink_band_noise_X.^2 + pink_band_noise_Y.^2);

% Plot resultant signal
subplot(3,1,3);
plot(resultant_noise);
title('Resultant Signal');
xlabel('Samples');
ylabel('Amplitude');

% Compute the power spectrum using Welch's method for Y
[Pxx_Y, F_Y] = pwelch(pink_band_noise_Y, [], [], [], fs);

% Compute the power spectrum using Welch's method for X
[Pxx_X, F_X] = pwelch(pink_band_noise_X, [], [], [], fs);

% Compute the power spectrum using Welch's method for resultant signal
[Pxx_R, F_R] = pwelch(resultant_noise, [], [], [], fs);

% Plot the log-log power spectrum for Y
figure;
loglog(F_Y, Pxx_Y);
xlim([f_low f_high]);
xlabel('Frequency (Hz)');
ylabel('Power');
title('Log-Log Power Spectrum of Filtered Pink Noise Y');

% Plot the log-log power spectrum for X
figure;
loglog(F_X, Pxx_X);
xlim([f_low f_high]);
xlabel('Frequency (Hz)');
ylabel('Power');
title('Log-Log Power Spectrum of Filtered Pink Noise X');

% Plot the log-log power spectrum for resultant signal
figure;
loglog(F_R, Pxx_R);
xlim([f_low f_high]);
xlabel('Frequency (Hz)');
ylabel('Power');
title('Log-Log Power Spectrum of Resultant Signal');
pink_band_noise_Y= pink_band_noise_Y.'
pink_band_noise_X= pink_band_noise_X.'
resultant_noise= resultant_noise.'
% Save the data to Excel
xlswrite('FilteredPinknoiseY.xlsx', pink_band_noise_Y);
xlswrite('FilteredPinknoiseX.xlsx', pink_band_noise_X);
xlswrite('FilteredResultantPinknoise.xlsx', resultant_noise);

% Play the filtered pink noises
sound(pink_band_noise_Y, fs);
pause(length(pink_band_noise_Y)/fs + 1); % Wait until the sound finishes playing
sound(pink_band_noise_X, fs);
