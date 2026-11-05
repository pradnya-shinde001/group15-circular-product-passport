
from subsystem1_passport import User, Product, MaterialComponent, Passport


def heading(title):
    print(f"\n--- {title} ---")


def main():
    heading("User")
    user = User("anna@example.com", role="manufacturer", password="s3cretPass!")
    print(user)
    print("Can edit:", user.can_edit())
    print("Password ok:", user.check_password("s3cretPass!"))

    heading("Product")
    laptop = Product("EcoBook 14", "laptop", lifespan_years=6, model="EB-14", owner=user)
    print("Created EcoBook 14")

    heading("MaterialComponent")
    laptop.add_material(MaterialComponent("aluminium", 60, recycled=True))
    laptop.add_material(MaterialComponent("plastic", 30))
    laptop.add_material(MaterialComponent("lithium battery", 10, hazard=True))
    print("Added aluminium (60%), plastic (30%), lithium battery (10%)")

    heading("Passport")
    passport = Passport(laptop)
    passport.add_history_event("Registered by manufacturer")
    print(passport.export_json())

    heading("QRCode")
    qr = passport.get_qr_code()
    print("Target URL:", qr.get_target_url())
    qr.save("passport_qr.png")
    print("Saved to passport_qr.png")

    heading("Validation")
    bad = Product("Broken", "phone", 3)
    bad.add_material(MaterialComponent("glass", 50))
    try:
        Passport(bad)
    except ValueError as err:
        print("Rejected:", err)


if __name__ == "__main__":
    main()
