package com.logentries.lighthouse;

public class AccessDeniedLighthouseException extends LighthouseException {
	private static final long serialVersionUID = -5354321793219341363L;

	private final String mUrl;

	private static String calcMsg(final String url) {
		return "Access Denied: " + url;
	}

	public AccessDeniedLighthouseException(final String url) {
		super(calcMsg(url));
		mUrl = url;
	}

	public AccessDeniedLighthouseException(final String url, final java.io.FileNotFoundException caused) {
		super(calcMsg(url), caused);
		mUrl = url;
	}

	public String getUrl() {
		return mUrl;
	}
};
