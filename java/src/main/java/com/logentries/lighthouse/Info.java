package com.logentries.lighthouse;

public class Info {
	private int mVersion;
	private String mChecksum;

	public Info(final int version, final String checksum) {
		if (version < 0) {
			throw new IllegalArgumentException("version should be >= 0");
		}
		mVersion = version;
		mChecksum = checksum;
	}

	public String toString() {
		return String.format("{version:%d; checksum:%s}", mVersion, mChecksum);
	}
}
