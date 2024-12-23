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

% Generate white noise for Y
n = fs * duration;     % Number of samples
white_noise_Y = randn(1, n); % Generate white noise
% Normalize amplitude for Y
Y = white_noise_Y / max(abs(white_noise_Y)) * amplitude_range_Y(2);
% Apply bandpass filter for Y
% [b_band, a_band] = butter(2, [f_low f_high]/(fs/2), 'bandpass');
% Y = filter(b_band, a_band, Y);
%Y=detrend(Y);
% Plot Y signal
figure;
subplot(3,1,1);
plot(Y);
title('white Noise Y');
xlabel('Samples');
ylabel('Amplitude');
% Generate white noise for x
n = fs * duration;     % Number of samples
white_noise_X = randn(1, n); % Generate white noise
% Normalize amplitude for x
X = white_noise_X / max(abs(white_noise_X)) * amplitude_range_X(2);
% Apply bandpass filter for Y
% [b_band, a_band] = butter(2, [f_low f_high]/(fs/2), 'bandpass');
% X = filter(b_band, a_band, X);
%X=detrend(X);
% Plot X signal
subplot(3,1,2);
plot(X);
title('White Noise X');
xlabel('Samples');
ylabel('Amplitude');
% Compute resultant signal
resultant_noise = sqrt(X.^2 + Y.^2);

% Plot resultant signal
subplot(3,1,3);
plot(resultant_noise);
title('Resultant Signal');
xlabel('Samples');
ylabel('Amplitude');
% Compute the power spectrum using Welch's method for Y
[Pxx_Y, F_Y] = pwelch(Y, [], [], [], fs);

% Compute the power spectrum using Welch's method for X
[Pxx_X, F_X] = pwelch(X, [], [], [], fs);

% Compute the power spectrum using Welch's method for resultant signal
[Pxx_R, F_R] = pwelch(resultant_noise, [], [], [], fs);
% Plot the log-log power spectrum for Y
figure;
loglog(F_Y, Pxx_Y);
xlim([f_low f_high]);
xlabel('Frequency (Hz)');
ylabel('Power');
title('Log-Log Power Spectrum of white Noise Y');

% Plot the log-log power spectrum for X
figure;
loglog(F_X, Pxx_X);
xlim([f_low f_high]);
xlabel('Frequency (Hz)');
ylabel('Power');
title('Log-Log Power Spectrum of white Noise X');

% Plot the log-log power spectrum for resultant signal
figure;
loglog(F_R, Pxx_R);
xlim([f_low f_high]);
xlabel('Frequency (Hz)');
ylabel('Power');
title('Log-Log Power Spectrum of Resultant Signal');
Y= Y.';
X= X.';
resultant_noise= resultant_noise.';
% Save the data to Excel
xlswrite('whiteNoiseY.xlsx', Y);
xlswrite('whiteNoiseX.xlsx', X);
xlswrite('whiteNoiseResultant.xlsx', resultant_noise);

