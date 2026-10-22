class FarmerProfile {
  final int id;
  final String fullName;
  final String? phone;
  final String preferredLanguage;

  const FarmerProfile({
    required this.id,
    required this.fullName,
    required this.phone,
    required this.preferredLanguage,
  });

  factory FarmerProfile.fromJson(Map<String, dynamic> json) {
    return FarmerProfile(
      id: (json['id'] as num).toInt(),
      fullName: json['full_name'] as String,
      phone: json['phone'] as String?,
      preferredLanguage: json['preferred_language'] as String? ?? 'en',
    );
  }
}
