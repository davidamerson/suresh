package com.suresh.srilankatv;

import android.content.Context;
import android.content.SharedPreferences;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.net.HttpURLConnection;
import java.net.URL;

public final class PlaylistStore {
    private static final String PREFS = "srilankatv";
    private static final String CUSTOM_M3U = "custom_m3u";
    private static final String ONLINE_M3U = "cached_remote_m3u";
    public static final String CATALOG_URL = "https://raw.githubusercontent.com/davidamerson/suresh/sltv-dual-tv-apps-20261109/SriLankaTV/app/src/main/assets/verified_channels.m3u";
    private PlaylistStore() {}

    public static final class Channel {
        public final String name;
        public final String url;
        public Channel(String name, String url) { this.name = name; this.url = url; }
    }

    public static List<Channel> getChannels(Context context) {
        String custom = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(CUSTOM_M3U, "");
        if (custom != null && !custom.trim().isEmpty()) {
            List<Channel> parsed = filterForApp(parse(custom));
            if (!parsed.isEmpty()) return parsed;
        }
        String online = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(ONLINE_M3U, "");
        if (online != null && !online.trim().isEmpty()) {
            List<Channel> parsed = filterForApp(parse(online));
            if (!parsed.isEmpty()) return parsed;
        }
        try (InputStream stream = context.getAssets().open("verified_channels.m3u")) {
            return filterForApp(parse(readAll(stream)));
        } catch (IOException e) {
            return Collections.emptyList();
        }
    }

    private static List<Channel> filterForApp(List<Channel> all) {
        if (!BuildConfig.FLAVOR.equals("sltvbridge")) return all;
        List<Channel> selected = new ArrayList<>();
        for (Channel ch : all) {
            if (ch.url.startsWith("https://sltv-app.thundercat.workers.dev/")
                || ch.url.startsWith("https://sltv-nice-face.thundercat.workers.dev/")) {
                selected.add(ch);
            }
        }
        return selected;
    }

    public static List<Channel> refresh(Context ctx) throws IOException {
        HttpURLConnection conn = (HttpURLConnection)new URL(CATALOG_URL).openConnection();
        conn.setConnectTimeout(12000);
        conn.setReadTimeout(12000);
        conn.setRequestProperty("User-Agent", "SriLankaTV/1.0");
        try {
            if (conn.getResponseCode() != 200) throw new IOException("HTTP "+conn.getResponseCode());
            String data = readAll(conn.getInputStream());
            List<Channel> all = parse(data);
            if (all.size() < 10) throw new IOException("Catalogue has too few entries");
            ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(ONLINE_M3U,data).apply();
            return getChannels(ctx);
        } finally { conn.disconnect(); }
    }

    public static boolean usingCustom(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .contains(CUSTOM_M3U);
    }

    public static void saveCustom(Context context, String playlist) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(CUSTOM_M3U, playlist).apply();
    }

    public static void clearCustom(Context context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().remove(CUSTOM_M3U).apply();
    }

    public static List<Channel> parse(String playlist) {
        List<Channel> items = new ArrayList<>();
        String title = "";
        try (BufferedReader reader = new BufferedReader(new StringReader(playlist))) {
            String line;
            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (line.startsWith("#EXTINF:")) {
                    int comma = line.lastIndexOf(',');
                    title = comma >= 0 ? line.substring(comma + 1).trim() : "";
                } else if (line.startsWith("https://") || line.startsWith("http://")) {
                    if (items.size() >= 1000) break;
                    if (title.isEmpty()) title = "Channel " + (items.size() + 1);
                    items.add(new Channel(title, line));
                    title = "";
                }
            }
        } catch (IOException ignored) {}
        return items;
    }

    public static String readAll(InputStream input) throws IOException {
        BufferedReader reader = new BufferedReader(
            new InputStreamReader(input, StandardCharsets.UTF_8));
        StringBuilder text = new StringBuilder();
        char[] buf = new char[8192];
        int n;
        while ((n = reader.read(buf)) > 0) {
            text.append(buf, 0, n);
            if (text.length() > 1_000_000) throw new IOException("Playlist is too large");
        }
        return text.toString();
    }
}
