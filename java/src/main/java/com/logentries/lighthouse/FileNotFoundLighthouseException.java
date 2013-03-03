package com.logentries.lighthouse;

public class FileNotFoundLighthouseException extends LighthouseException {
	private final String mUrl;

	private static String calcMsg(final String url) {
		return "Not found: " + url;
	}

	public FileNotFoundLighthouseException(final String url, java.io.FileNotFoundException caused) {
		super(calcMsg(url), caused);
		mUrl = url;
	}

	public FileNotFoundLighthouseException(final String url) {
		super(calcMsg(url));
		mUrl = url;
	}

	public String getUrl() {
		return mUrl;
	}
};
