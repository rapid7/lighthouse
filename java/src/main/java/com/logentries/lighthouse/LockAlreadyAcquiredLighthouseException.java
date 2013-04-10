package com.logentries.lighthouse;

public class LockAlreadyAcquiredLighthouseException extends LighthouseException {
	private static final long serialVersionUID = 1951405008874521687L;

	public LockAlreadyAcquiredLighthouseException() {
		super("Lock Already Acquired");
	}
}
