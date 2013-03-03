package com.logentries.lighthouse;

public class BadStatusCodeLighthouseException extends LighthouseException {
	public BadStatusCodeLighthouseException(final int code) {
		super("Unexpected status code: " + code);	
	}
}
