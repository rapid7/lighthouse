package com.logentries.lighthouse;

public class LockNotAcquiredLighthouseException extends LighthouseException {
	private static final long serialVersionUID = 4015733374668413606L;

	public LockNotAcquiredLighthouseException() {
		super("Lock Not Acquired");
	}
}
