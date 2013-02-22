package com.logentries.lighthouse;

import java.net.URLConnection;
import java.net.URL;
import java.nio.charset.Charset;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.Date;
import java.util.Map;
import org.json.simple.JSONValue;

/**
 * Logentries client for Lighthouse server.
 * 
 * VERSION: 1.0.0
 * 
 * @author Daniel Fiala
 * 
 */
public class LighthouseClient {
	static final Charset HTTP_CHARSET = Charset.forName("utf-8");

	static final String PATH_INFO = "info";
	static final String PATH_DATA = "data";
	static final String PATH_PULL = "pull";

	private String mHost;
	private int mPort;

	public LighthouseClient(final String host, final int port) {
		mHost = host;
		mPort = port;
	}

	private String url(final String path) {
		return String.format("http://%s:%d/%s", mHost, mPort, path);
	}

	private Object req_get(final String path) throws LighthouseException {
		final String u = url(path);
		try {
			final URLConnection conn = new URL(u).openConnection();
			int len = conn.getContentLength();
			return JSONValue.parseWithException(new InputStreamReader(conn.getInputStream(), HTTP_CHARSET));
		} catch (java.net.MalformedURLException e) {
			throw new LighthouseException(e);
		} catch (java.io.FileNotFoundException e) {
			throw new FileNotFoundLighthouseException(u, e);
		} catch (java.io.IOException e) {
			throw new LighthouseException(e);
		} catch (org.json.simple.parser.ParseException e) {
			throw new LighthouseException(e);
		}
	}

	private static Info mapToInfo(final Map map) {
		return new Info(((Number)map.get("version")).intValue(), (String)map.get("checksum"));
	}

	public Info info() throws LighthouseException {
		final Object ans = req_get(PATH_INFO);
		Map map = (Map)ans;
		return mapToInfo(map);
	}

	public Map data(final String tail) throws LighthouseException {
		final Object ans = req_get(PATH_DATA + tail);
		return (Map)ans;
	}

	public Pull pull() throws LighthouseException {
		final Object ans = req_get(PATH_PULL);
		final Map map = (Map)ans;
		return new Pull(mapToInfo(map), (Map)map.get("data"));
	}
}
