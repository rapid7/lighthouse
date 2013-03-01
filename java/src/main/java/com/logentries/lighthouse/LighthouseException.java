package com.logentries.lighthouse;

public class LighthouseException extends java.lang.Exception {
	public LighthouseException() {
	}

	public LighthouseException(final Throwable cause) {
		super(cause);
	}

	public LighthouseException(final String msg) {
		super(msg);
	}

	public LighthouseException(final String msg, final Throwable cause) {
		super(msg, cause);
	}
}
