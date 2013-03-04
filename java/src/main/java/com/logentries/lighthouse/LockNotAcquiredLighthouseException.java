package com.logentries.lighthouse;

public class LockNotAcquiredLighthouseException extends LighthouseException {
	public LockNotAcquiredLighthouseException() {
		super("Lock Not Acquired");
	}
}
