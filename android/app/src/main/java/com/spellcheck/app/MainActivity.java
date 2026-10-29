package com.spellcheck.app;

import android.app.Activity;
import android.content.Context;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final String PREFS = "spellcheck";
    private static final String API_URL_KEY = "api_url";
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private EditText apiUrlInput;
    private EditText textInput;
    private CheckBox grammarCheckbox;
    private Button checkButton;
    private TextView statusView;
    private TextView resultsView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        int padding = dp(20);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(padding, padding, padding, padding);

        TextView title = new TextView(this);
        title.setText("Spellcheck");
        title.setTextSize(28);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        content.addView(title, matchWrap());

        TextView apiLabel = label("Python API address");
        content.addView(apiLabel, matchWrap());
        apiUrlInput = new EditText(this);
        apiUrlInput.setSingleLine(true);
        apiUrlInput.setHint("https://your-spellcheck-server.example");
        apiUrlInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        apiUrlInput.setText(getSharedPreferences(PREFS, MODE_PRIVATE)
                .getString(API_URL_KEY, ""));
        content.addView(apiUrlInput, matchWrap());

        content.addView(label("Text to check"), matchWrap());
        textInput = new EditText(this);
        textInput.setGravity(android.view.Gravity.TOP | android.view.Gravity.START);
        textInput.setHint("Paste or type your text here");
        textInput.setMinLines(6);
        textInput.setMaxLines(12);
        textInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE
                | android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        content.addView(textInput, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(180)));

        grammarCheckbox = new CheckBox(this);
        grammarCheckbox.setText("Check grammar and style");
        grammarCheckbox.setChecked(true);
        content.addView(grammarCheckbox, matchWrap());

        checkButton = new Button(this);
        checkButton.setText("Check text");
        content.addView(checkButton, matchWrap());
        statusView = label("");
        content.addView(statusView, matchWrap());
        resultsView = label("");
        resultsView.setTextIsSelectable(true);
        content.addView(resultsView, matchWrap());

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(content);
        setContentView(scroll);

        checkButton.setOnClickListener(view -> submitCheck());
    }

    private void submitCheck() {
        String baseUrl = apiUrlInput.getText().toString().trim().replaceAll("/+$", "");
        String text = textInput.getText().toString();
        boolean secureUrl = baseUrl.startsWith("https://");
        boolean debugHttpUrl = BuildConfig.ALLOW_HTTP && baseUrl.startsWith("http://");
        if (!secureUrl && !debugHttpUrl) {
            statusView.setText("Use an HTTPS API address. Debug builds also allow HTTP.");
            return;
        }
        if (text.trim().isEmpty()) {
            statusView.setText("Enter some text to check.");
            return;
        }

        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(API_URL_KEY, baseUrl).apply();
        ((InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE))
                .hideSoftInputFromWindow(textInput.getWindowToken(), 0);
        checkButton.setEnabled(false);
        statusView.setText("Checking…");
        resultsView.setText("");
        boolean grammar = grammarCheckbox.isChecked();

        executor.execute(() -> {
            try {
                JSONObject request = new JSONObject();
                request.put("text", text);
                request.put("grammar", grammar);
                JSONObject response = postCheck(baseUrl + "/check", request);
                String formatted = formatResults(response, grammar);
                runOnUiThread(() -> {
                    resultsView.setText(formatted);
                    statusView.setText("Check complete.");
                    checkButton.setEnabled(true);
                });
            } catch (Exception exception) {
                String message = exception.getMessage() == null
                        ? "The check failed." : exception.getMessage();
                runOnUiThread(() -> {
                    statusView.setText(message);
                    checkButton.setEnabled(true);
                });
            }
        });
    }

    private JSONObject postCheck(String endpoint, JSONObject body) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(endpoint).openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(15000);
        connection.setReadTimeout(60000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);
        if (payload.length > 1_000_000) {
            connection.disconnect();
            throw new Exception("Text is too large. Keep the request under 1 MB.");
        }
        try (OutputStream output = connection.getOutputStream()) {
            output.write(payload);
        }
        int code = connection.getResponseCode();
        InputStream stream = code >= 400 ? connection.getErrorStream() : connection.getInputStream();
        if (stream == null) {
            connection.disconnect();
            throw new Exception("The API returned HTTP " + code + " without a response body.");
        }
        String responseText;
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            StringBuilder result = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) result.append(line);
            responseText = result.toString();
        } finally {
            connection.disconnect();
        }
        JSONObject response = new JSONObject(responseText);
        if (code < 200 || code >= 300) {
            throw new Exception(response.optString("error", "The API returned HTTP " + code));
        }
        return response;
    }

    private String formatResults(JSONObject response, boolean grammar) throws JSONException {
        StringBuilder result = new StringBuilder();
        String warning = response.optString("warning", "");
        if (!warning.isEmpty()) result.append("Warning: ").append(warning).append("\n\n");
        appendSpelling(result, response.optJSONArray("spelling"));
        if (grammar) appendGrammar(result, response.optJSONArray("grammar"));
        return result.toString().trim();
    }

    private void appendSpelling(StringBuilder result, JSONArray items) throws JSONException {
        result.append("Spelling");
        int count = items == null ? 0 : items.length();
        result.append(" (").append(count).append(")\n");
        if (count == 0) result.append("No spelling issues found.\n");
        for (int i = 0; i < count; i++) {
            JSONObject item = items.getJSONObject(i);
            result.append("• ").append(item.optString("word"))
                    .append(" at position ").append(item.optInt("position"))
                    .append(" — Suggestions: ")
                    .append(join(item.optJSONArray("suggestions"))).append('\n');
        }
        result.append('\n');
    }

    private void appendGrammar(StringBuilder result, JSONArray items) throws JSONException {
        result.append("Grammar and style");
        int count = items == null ? 0 : items.length();
        result.append(" (").append(count).append(")\n");
        if (count == 0) result.append("No grammar issues found.\n");
        for (int i = 0; i < count; i++) {
            JSONObject item = items.getJSONObject(i);
            result.append("• ").append(item.optString("issue_type"))
                    .append(" at position ").append(item.optInt("offset"))
                    .append(" — ").append(item.optString("message"));
            String replacements = join(item.optJSONArray("replacements"));
            if (!replacements.isEmpty()) result.append(" Suggestions: ").append(replacements);
            result.append('\n');
        }
    }

    private String join(JSONArray items) {
        if (items == null || items.length() == 0) return "none";
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < items.length(); i++) {
            if (i > 0) result.append(", ");
            result.append(items.optString(i));
        }
        return result.toString();
    }

    private TextView label(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(16);
        view.setPadding(0, dp(10), 0, dp(4));
        return view;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }
}
