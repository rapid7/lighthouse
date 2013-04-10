package com.logentries.lighthouse;

public class ResponseConflictLighthouseException extends LighthouseException {
	private static final long serialVersionUID = 9066203812295577315L;

	private final String mUrl;

	private static String calcMsg(final String url) {
		return "Response Conflict: " + url;
	}

	public ResponseConflictLighthouseException(final String url) {
		super(calcMsg(url));
		mUrl = url;
	}

	public String getUrl() {
		return mUrl;
	}
};
