package lk.openstream.tv.common;

import org.json.JSONObject;
public final class Channel {
    public final String id;
    public final String name;
    public final String category;
    public final String url;
    public final String access;
    public Channel(String id,String name,String category,String url,String access) {
        this.id=id;this.name=name;this.category=category;this.url=url;this.access=access;
    }
    public static Channel fromJson(JSONObject j) {
        return new Channel(j.optString("id",""),j.optString("name","Unknown"),
            j.optString("category","Other"),j.optString("url",""),j.optString("access","unresolved"));
    }
    public boolean canPlayDirectly() {
        return "public_candidate".equals(access) &&
            (url.startsWith("https://") || url.startsWith("http://")) &&
            !url.contains("<id>");
    }
    public String status() {
        if (canPlayDirectly()) return "PUBLIC STREAM CANDIDATE";
        if ("sltv_backend".equals(access)) return "SLTV SERVER · ORIGINAL APP";
        if ("provider_restricted".equals(access)) return "PROVIDER ACCESS REQUIRED";
        return "UNVERIFIED STREAM";
    }
}
