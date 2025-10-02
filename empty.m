function plot_reports_matlab(dataDir, outputDir)
if nargin < 1 || isempty(dataDir)
    dataDir = 'data_report';
end
if nargin < 2 || isempty(outputDir)
    outputDir = 'figures_matlab';
end
reports = dir(fullfile(dataDir, '*.rpt'));
if isempty(reports)
    error('No .rpt files found in %s', dataDir);
end
if ~exist(outputDir, 'dir')
    mkdir(outputDir);
end
[engFont, chiFont] = resolve_fonts();
default_label_x = mixed_font_text('位移/mm', engFont, chiFont);
default_label_y = mixed_font_text('荷载/kN', engFont, chiFont);
allSeries = cell(1, numel(reports));
for k = 1:numel(reports)
    series = load_report(fullfile(dataDir, reports(k).name));
    allSeries{k} = series;
    fig = figure('Visible', 'off', 'Units', 'centimeters');
    fig.Position(3:4) = [8 6];
    ax = axes('Parent', fig);
    hold(ax, 'on');
    plot(ax, series.x, series.y, 'LineWidth', 1.0, 'Marker', 'o', 'MarkerSize', 2.0, ...
        'MarkerFaceColor', 'none', 'MarkerEdgeColor', ax.ColorOrder(1,:), 'MarkerEdgeWidth', 0.8);
    xlabel(ax, default_label_x, 'Interpreter', 'tex');
    ylabel(ax, default_label_y, 'Interpreter', 'tex');
    title(ax, mixed_font_text(series.title, engFont, chiFont), 'Interpreter', 'tex', 'FontSize', 10);
    grid(ax, 'on');
    ax.GridLineStyle = '--';
    ax.GridAlpha = 0.5;
    ax.LineWidth = 0.4;
    ax.FontName = engFont;
    legend(ax, mixed_font_text(series.title, engFont, chiFont), 'Location', 'best', ...
        'Interpreter', 'tex', 'Box', 'off');
    print(fig, fullfile(outputDir, [series.safeName '.svg']), '-dsvg');
    close(fig);
end
grouped = group_series(allSeries);
keys = string(fieldnames(grouped));
for i = 1:numel(keys)
    key = keys(i);
    groupSeries = grouped.(key);
    if numel(groupSeries) < 2
        continue;
    end
    plot_group(groupSeries, fullfile(outputDir, ['comparison_' char(key) '.svg']), ...
        engFont, chiFont, default_label_x, default_label_y, char(key));
end
if numel(allSeries) > 1
    plot_group(allSeries, fullfile(outputDir, 'comparison_all.svg'), engFont, chiFont, ...
        default_label_x, default_label_y, 'All Series Comparison');
end
end

function series = load_report(path)
fid = fopen(path, 'r');
if fid == -1
    error('Cannot open %s', path);
end
cleanup = onCleanup(@() fclose(fid));
rawX = [];
rawY = [];
header = {};
while true
    line = fgetl(fid);
    if ~ischar(line)
        break;
    end
    line = strtrim(line);
    if isempty(line)
        continue;
    end
    tokens = strsplit(line);
    if is_data_line(tokens)
        rawX(end+1) = str2double(tokens{1}); %#ok<AGROW>
        rawY(end+1) = str2double(tokens{2}) * 1e-3; %#ok<AGROW>
    else
        header{end+1} = line; %#ok<AGROW>
    end
end
if isempty(header)
    header = {};
end
[~, baseName, ~] = fileparts(path);
series.name = baseName;
if isempty(header)
    series.title = baseName;
else
    series.title = header{1};
end
series.safeName = regexprep(baseName, '\s+', '_');
series.x = rawX;
series.y = rawY;
end

function tf = is_data_line(tokens)
if numel(tokens) < 2
    tf = false;
    return;
end
x = str2double(tokens{1});
y = str2double(tokens{2});
tf = ~(isnan(x) || isnan(y));
end

function grouped = group_series(seriesCell)
keys = strings(1, numel(seriesCell));
for i = 1:numel(seriesCell)
    name = string(seriesCell{i}.safeName);
    dash = strfind(name, '-');
    if isempty(dash)
        keys(i) = name;
    else
        keys(i) = extractBefore(name, dash(1));
    end
end
uniqueKeys = unique(keys);
for k = 1:numel(uniqueKeys)
    idx = keys == uniqueKeys(k);
    grouped.(uniqueKeys(k)) = seriesCell(idx);
end
end

function plot_group(seriesCell, outPath, engFont, chiFont, xlabelText, ylabelText, key)
fig = figure('Visible', 'off', 'Units', 'centimeters');
fig.Position(3:4) = [8 6];
ax = axes('Parent', fig);
hold(ax, 'on');
for i = 1:numel(seriesCell)
    series = seriesCell{i};
    weight = 1.0;
    if contains(lower(series.safeName), 'base')
        weight = 1.4;
    end
    plot(ax, series.x, series.y, 'DisplayName', mixed_font_text(series.title, engFont, chiFont), ...
        'LineWidth', weight, 'Marker', 'o', 'MarkerSize', 2.0, 'MarkerFaceColor', 'none', ...
        'MarkerEdgeWidth', 0.8);
end
xlabel(ax, xlabelText, 'Interpreter', 'tex');
ylabel(ax, ylabelText, 'Interpreter', 'tex');
title(ax, mixed_font_text(sprintf('Comparison – %s', key), engFont, chiFont), ...
    'Interpreter', 'tex', 'FontSize', 10);
grid(ax, 'on');
ax.GridLineStyle = '--';
ax.GridAlpha = 0.5;
ax.LineWidth = 0.4;
ax.FontName = engFont;
leg = legend(ax, 'show', 'Location', 'best', 'Interpreter', 'tex', 'Box', 'off'); %#ok<NASGU>
print(fig, outPath, '-dsvg');
close(fig);
end

function [engFont, chiFont] = resolve_fonts()
fonts = listfonts;
engFont = 'Times New Roman';
if ~any(strcmpi(fonts, engFont))
    engFont = fonts{1};
end
chiFont = 'SimSun';
if ~any(strcmpi(fonts, chiFont))
    chiFont = engFont;
end
end

function out = mixed_font_text(text, engFont, chiFont)
chars = char(text);
segments = strings(1, 0);
currentFont = '';
currentSegment = "";
for i = 1:numel(chars)
    ch = chars(i);
    if is_chinese_char(ch)
        fontName = chiFont;
    else
        fontName = engFont;
    end
    if ~strcmp(fontName, currentFont)
        if strlength(currentSegment) > 0
            segments(end+1) = currentSegment; %#ok<AGROW>
        end
        currentSegment = "\fontname{" + fontName + "}" + string(ch);
        currentFont = fontName;
    else
        currentSegment = currentSegment + string(ch);
    end
end
if strlength(currentSegment) > 0
    segments(end+1) = currentSegment;
end
out = char(strjoin(segments, ''));
end

function tf = is_chinese_char(ch)
code = double(ch);
tf = code >= hex2dec('4E00') && code <= hex2dec('9FFF');
end
