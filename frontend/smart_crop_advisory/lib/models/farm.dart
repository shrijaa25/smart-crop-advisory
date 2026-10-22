class Farm {
  final int id;
  final String name;
  final String? village;
  final String? district;
  final String? state;
  final double? latitude;
  final double? longitude;
  final double? areaValue;
  final String areaUnit;
  final String? soilType;
  final String? irrigationMethod;

  const Farm({
    required this.id,
    required this.name,
    required this.village,
    required this.district,
    required this.state,
    required this.latitude,
    required this.longitude,
    required this.areaValue,
    required this.areaUnit,
    required this.soilType,
    required this.irrigationMethod,
  });

  factory Farm.fromJson(Map<String, dynamic> json) => Farm(
    id: (json['id'] as num).toInt(),
    name: json['name'] as String,
    village: json['village'] as String?,
    district: json['district'] as String?,
    state: json['state'] as String?,
    latitude: (json['latitude'] as num?)?.toDouble(),
    longitude: (json['longitude'] as num?)?.toDouble(),
    areaValue: (json['area_value'] as num?)?.toDouble(),
    areaUnit: json['area_unit'] as String? ?? 'acre',
    soilType: json['soil_type'] as String?,
    irrigationMethod: json['irrigation_method'] as String?,
  );
}
