package com.logentries.lighthouse;

public class BadStatusCodeLighthouseException extends LighthouseException {
	private static final long serialVersionUID = -1152192618513809091L;

	public BadStatusCodeLighthouseException(final int code) {
		super("Unexpected status code: " + code);	
	}
}
