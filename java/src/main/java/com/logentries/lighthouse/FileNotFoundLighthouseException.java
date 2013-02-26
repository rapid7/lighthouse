package com.logentries.lighthouse;

public class FileNotFoundLighthouseException extends LighthouseException {
	private final String mUrl;

	public FileNotFoundLighthouseException(final String url, final java.io.FileNotFoundException caused) {
		super(caused);
		mUrl = url;
	}

	public String getUrl() {
		return mUrl;
	}
};
